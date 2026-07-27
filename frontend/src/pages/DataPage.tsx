import { useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { ProfileStateGate } from '../components/ProfileStateGate'
import { TrophyFilters } from '../components/TrophyFilters'
import { TrophyTable } from '../components/TrophyTable'
import type { Trophy } from '../lib/api'
import { downloadCsv } from '../lib/csv'
import {
  createDefaultFilters,
  dataRowsToCsv,
  filterDataRows,
  toDataRows,
  type DataFilters,
} from '../lib/dataTable'
import { useProfile } from '../lib/queries'

export function DataPage() {
  const { username } = useParams<{ username: string }>()
  const profileQuery = useProfile(username)

  return (
    <ProfileStateGate username={username} query={profileQuery}>
      {(data) => <DataContent username={username ?? ''} trophyLog={data.trophy_log} />}
    </ProfileStateGate>
  )
}

function DataContent({ username, trophyLog }: { username: string; trophyLog: Trophy[] }) {
  const rows = useMemo(() => toDataRows(trophyLog), [trophyLog])
  const [filters, setFilters] = useState<DataFilters>(createDefaultFilters)

  const filteredRows = useMemo(() => filterDataRows(rows, filters), [rows, filters])

  function handleDownload() {
    downloadCsv(`${username || 'trophies'}-trophies.csv`, dataRowsToCsv(filteredRows))
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-lg font-semibold text-text">Trophy Data</h1>
        <button
          type="button"
          onClick={handleDownload}
          disabled={filteredRows.length === 0}
          className="rounded-lg bg-accent px-3 py-1.5 text-sm font-medium text-bg transition hover:bg-accent-bright disabled:cursor-not-allowed disabled:opacity-50"
        >
          Download CSV
        </button>
      </div>

      <TrophyFilters filters={filters} onChange={setFilters} />

      <p className="text-sm text-muted">
        Showing {filteredRows.length.toLocaleString()} of {rows.length.toLocaleString()} trophies
      </p>

      <TrophyTable rows={filteredRows} />
    </div>
  )
}
