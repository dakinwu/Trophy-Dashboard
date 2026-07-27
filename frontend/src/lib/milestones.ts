import type { Trophy } from './api'
import { formatDuration, getFastestPlatinumsByGame, sortTrophiesByTime } from './trophy'

export interface Milestone {
  key: string
  icon: string
  title: string
  game: string
  trophyTitle: string
  date: Date
}

/**
 * Notable moments derived from the trophy log: firsts, records, and
 * round-number counters. Returned in chronological order.
 */
export function computeMilestones(trophies: Trophy[]): Milestone[] {
  const sorted = sortTrophiesByTime(trophies)
  if (sorted.length === 0) return []

  const milestones: Milestone[] = []

  const first = sorted[0]
  milestones.push({
    key: 'first-trophy',
    icon: '🎮',
    title: 'First Trophy',
    game: first.game,
    trophyTitle: first.title,
    date: first.parsedDate,
  })

  const platinums = sorted.filter((trophy) => trophy.grade === 'Platinum')

  if (platinums.length > 0) {
    const firstPlatinum = platinums[0]
    milestones.push({
      key: 'first-platinum',
      icon: '🏆',
      title: 'First Platinum',
      game: firstPlatinum.game,
      trophyTitle: firstPlatinum.title,
      date: firstPlatinum.parsedDate,
    })

    const latestPlatinum = platinums[platinums.length - 1]
    if (latestPlatinum !== firstPlatinum) {
      milestones.push({
        key: 'latest-platinum',
        icon: '✨',
        title: 'Latest Platinum',
        game: latestPlatinum.game,
        trophyTitle: latestPlatinum.title,
        date: latestPlatinum.parsedDate,
      })
    }
  }

  const [fastest] = getFastestPlatinumsByGame(trophies)
  if (fastest) {
    milestones.push({
      key: 'fastest-platinum',
      icon: '⚡',
      title: `Fastest Platinum — ${formatDuration(fastest.durationMs)}`,
      game: fastest.game,
      trophyTitle: fastest.platinum.title,
      date: fastest.platinum.parsedDate,
    })
  }

  for (let n = 1000; n <= sorted.length; n += 1000) {
    const trophy = sorted[n - 1]
    milestones.push({
      key: `trophy-${n}`,
      icon: '🎯',
      title: `${n.toLocaleString()}th Trophy`,
      game: trophy.game,
      trophyTitle: trophy.title,
      date: trophy.parsedDate,
    })
  }

  for (let n = 10; n <= platinums.length; n += 10) {
    const trophy = platinums[n - 1]
    milestones.push({
      key: `platinum-${n}`,
      icon: '💎',
      title: `${n.toLocaleString()}th Platinum`,
      game: trophy.game,
      trophyTitle: trophy.title,
      date: trophy.parsedDate,
    })
  }

  return milestones.sort((a, b) => a.date.getTime() - b.date.getTime())
}
