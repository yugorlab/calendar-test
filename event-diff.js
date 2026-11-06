(function (root) {
  'use strict';

  /**
   * Compare two calendar snapshots.
   *
   * Supported changes:
   * - new: a new active event appeared
   * - cancelled: an existing event was cancelled
   * - rescheduled: its start or end date changed
   *
   * Changes to names, languages, circles, descriptions and previews
   * are intentionally ignored.
   */

  function getEvents(snapshot) {
    if (Array.isArray(snapshot)) return snapshot;
    if (snapshot && Array.isArray(snapshot.events)) {
      return snapshot.events;
    }
    return [];
  }

  function compareEvents(previousSnapshot, currentSnapshot) {
    const previous = getEvents(previousSnapshot);
    const current = getEvents(currentSnapshot);

    const previousById = new Map();

    for (const event of previous) {
      if (event && event.id != null) {
        previousById.set(String(event.id), event);
      }
    }

    const changes = [];

    for (const event of current) {
      if (!event || event.id == null) continue;

      const id = String(event.id);
      const oldEvent = previousById.get(id);

      // A new event is reported only if it is not cancelled.
      if (!oldEvent) {
        if (event.cancelled !== true && event.status !== 'cancelled') {
          changes.push({
            type: 'new',
            eventId: id,
            name: String(event.name || 'Untitled event'),
            startDate: event.startDate || '',
            endDate: event.endDate || ''
          });
        }

        continue;
      }

      const wasCancelled =
        oldEvent.cancelled === true || oldEvent.status === 'cancelled';

      const isCancelled =
        event.cancelled === true || event.status === 'cancelled';

    // Cancellation takes priority over date changes.
      if (!wasCancelled && isCancelled) {
        changes.push({
          type: 'cancelled',
          eventId: id,
          name: String(event.name || oldEvent.name || 'Untitled event'),
          startDate: event.startDate || '',
          endDate: event.endDate || ''
        });

        continue;
      }

      // Ignore date changes if the event is currently cancelled.
      if (isCancelled) continue;

      const oldStart = String(oldEvent.startDate || '');
      const oldEnd = String(oldEvent.endDate || '');
      const newStart = String(event.startDate || '');
      const newEnd = String(event.endDate || '');

      if (oldStart !== newStart || oldEnd !== newEnd) {
        changes.push({
          type: 'rescheduled',
          eventId: id,
          name: String(event.name || oldEvent.name || 'Untitled event'),
          oldStartDate: oldStart,
          oldEndDate: oldEnd,
          startDate: newStart,
          endDate: newEnd
        });
      }
    }

    return changes;
  }

  // Make the function available in the browser.
  root.KyodoEventDiff = { compareEvents };

  // Also support Node.js tests, if available.
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { compareEvents };
  }

})(typeof globalThis !== 'undefined' ? globalThis : this);
