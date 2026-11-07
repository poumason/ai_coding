import type { Register, EngineInterfaceBuilt } from 'claude-code'

type Engine = EngineInterfaceBuilt

type Profile = {
  ANTHROPIC_BASE_URL?: string
  ANTHROPIC_AUTH_TOKEN?: string
  ANTHROPIC_MODEL?: string
  ANTHROPIC_SMALL_FAST_MODEL?: string
}

const ENV_KEYS = [
  'ANTHROPIC_BASE_URL',
  'ANTHROPIC_AUTH_TOKEN',
  'ANTHROPIC_MODEL',
  'ANTHROPIC_SMALL_FAST_MODEL',
] as const

async function homeDir($: Engine): Promise<string> {
  const home = await $.env.get('HOME')
  if (!home) throw new Error('HOME is not set')
  return home
}

async function profilesDir($: Engine): Promise<string> {
  return `${await homeDir($)}/.claude/profiles`
}

async function settingsPath($: Engine): Promise<string> {
  return `${await homeDir($)}/.claude/settings.json`
}

async function loadProfile($: Engine, name: string): Promise<Profile | undefined> {
  const path = `${await profilesDir($)}/${name}.json`
  if (!(await $.fs.exists(path))) return undefined
  return JSON.parse(await $.fs.read(path)) as Profile
}

async function listProfileNames($: Engine): Promise<string[]> {
  const dir = await profilesDir($)
  if (!(await $.fs.exists(dir))) return []
  const entries = await $.fs.list(dir)
  return entries
    .filter(e => e.kind === 'file' && e.name.endsWith('.json'))
    .map(e => e.name.slice(0, -5))
    .sort()
}

async function ensureSampleProfiles($: Engine): Promise<void> {
  const dir = await profilesDir($)
  if (await $.fs.exists(dir)) return
  await $.fs.write(
    `${dir}/cloud.json`,
    JSON.stringify(
      {
        ANTHROPIC_BASE_URL: 'https://api.anthropic.com',
        ANTHROPIC_AUTH_TOKEN: 'sk-ant-REPLACE-ME',
        ANTHROPIC_MODEL: 'claude-sonnet-5-5',
      },
      null,
      2,
    ) + '\n',
  )
  await $.fs.write(
    `${dir}/internal.json`,
    JSON.stringify(
      {
        ANTHROPIC_BASE_URL: 'https://REPLACE-ME.internal.example.com',
        ANTHROPIC_AUTH_TOKEN: 'REPLACE-ME',
        ANTHROPIC_MODEL: 'REPLACE-ME',
      },
      null,
      2,
    ) + '\n',
  )
}

async function readSettings($: Engine): Promise<Record<string, unknown>> {
  const path = await settingsPath($)
  if (!(await $.fs.exists(path))) return {}
  try {
    return JSON.parse(await $.fs.read(path)) as Record<string, unknown>
  } catch {
    return {}
  }
}

async function writeSettings($: Engine, settings: Record<string, unknown>): Promise<void> {
  const path = await settingsPath($)
  if (await $.fs.exists(path)) {
    await $.fs.write(`${path}.bak`, await $.fs.read(path))
  }
  await $.fs.write(path, JSON.stringify(settings, null, 2) + '\n')
}

async function setEnvVar(
  $: Engine,
  key: (typeof ENV_KEYS)[number],
  value: string,
): Promise<{ deny?: string }> {
  switch (key) {
    case 'ANTHROPIC_BASE_URL':
      return $.env.set('ANTHROPIC_BASE_URL', value)
    case 'ANTHROPIC_AUTH_TOKEN':
      return $.env.set('ANTHROPIC_AUTH_TOKEN', value)
    case 'ANTHROPIC_MODEL':
      return $.env.set('ANTHROPIC_MODEL', value)
    case 'ANTHROPIC_SMALL_FAST_MODEL':
      return $.env.set('ANTHROPIC_SMALL_FAST_MODEL', value)
  }
}

function activeProfileName(
  settings: Record<string, unknown>,
  profiles: Record<string, Profile>,
): string | undefined {
  const env = (settings.env as Record<string, string> | undefined) ?? {}
  for (const [name, profile] of Object.entries(profiles)) {
    const matches = ENV_KEYS.every(key => {
      const wanted = profile[key]
      return wanted === undefined || env[key] === wanted
    })
    if (matches) return name
  }
  return undefined
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await ensureSampleProfiles($)
    await $.command.register({
      name: 'profile',
      description: 'Switch model profile (cloud/internal); /profile list to see options',
      argumentHint: '<name>|list',
    })
    return next(e)
  })

  on('command.run', { command: 'profile' }, async ($, e, next) => {
    const arg = e.args.trim()
    const dir = await profilesDir($)

    if (arg === '' || arg === 'list') {
      const names = await listProfileNames($)
      if (names.length === 0) {
        return { text: `No profiles found in ${dir}.\nEdit the sample files there and run /profile <name>.` }
      }
      const settings = await readSettings($)
      const profiles: Record<string, Profile> = {}
      for (const name of names) {
        const profile = await loadProfile($, name)
        if (profile) profiles[name] = profile
      }
      const active = activeProfileName(settings, profiles)
      const lines = names.map(name => `${name === active ? '* ' : '  '}${name}`)
      return { text: `Profiles in ${dir}:\n${lines.join('\n')}\n\nUse: /profile <name>` }
    }

    const profile = await loadProfile($, arg)
    if (!profile) {
      const names = await listProfileNames($)
      return {
        text: `No profile named "${arg}" in ${dir}.\nAvailable: ${names.join(', ') || '(none yet — edit the sample files there)'}`,
      }
    }

    const applied: string[] = []
    const refused: string[] = []
    for (const key of ENV_KEYS) {
      const value = profile[key]
      if (value === undefined) continue
      const result = await setEnvVar($, key, value)
      if (result.deny) refused.push(`${key} (${result.deny})`)
      else applied.push(key)
    }

    const settings = await readSettings($)
    settings.env = { ...((settings.env as Record<string, unknown>) ?? {}), ...profile }
    await writeSettings($, settings)

    const lines = [
      `Switched to profile "${arg}".`,
      `Wrote ${await settingsPath($)} (previous version saved as .bak).`,
    ]
    if (applied.length > 0) {
      lines.push(
        `Also set ${applied.join(', ')} live on this process — new turns may pick it up right away.`,
      )
    }
    if (refused.length > 0) {
      lines.push(`Could not set live: ${refused.join(', ')}.`)
    }
    lines.push(
      'If the next reply still looks like the old provider/model, exit (Ctrl+D or /exit) and run `claude` again — the saved settings.json will apply on the fresh start.',
    )

    return { text: lines.join('\n') }
  })
}
