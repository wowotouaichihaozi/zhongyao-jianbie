import type { createClient } from '@libsql/client'

type LibSqlClient = ReturnType<typeof createClient>

/**
 * Patch: add version and style_case columns to styles table.
 */
export const patchStylesColumns = async (client: LibSqlClient): Promise<void> => {
  const cols = await client.execute("PRAGMA table_info('styles')")
  const columnNames = new Set(cols.rows.map((r) => r.name as string))

  if (!columnNames.has('version')) {
    await client.execute('ALTER TABLE styles ADD COLUMN version INTEGER NOT NULL DEFAULT 1')
  }
  if (!columnNames.has('style_case')) {
    await client.execute("ALTER TABLE styles ADD COLUMN style_case TEXT NOT NULL DEFAULT ''")
  }
  if (!columnNames.has('active')) {
    await client.execute('ALTER TABLE styles ADD COLUMN active INTEGER NOT NULL DEFAULT 1')
  }
}
