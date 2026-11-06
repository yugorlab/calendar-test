const { compareEvents } = require('./event-diff.js');

const previous = [
  {
    id: 'event-1',
    name: 'Old Event',
    startDate: '2026-11-10',
    endDate: '2026-11-12',
    cancelled: false
  },
  {
    id: 'event-2',
    name: 'Another Event',
    startDate: '2026-11-15',
    endDate: '2026-11-15',
    cancelled: false
  }
];

const current = [
  {
    id: 'event-1',
    name: 'Renamed Event',
    startDate: '2026-11-11',
    endDate: '2026-11-13',
    cancelled: false
  },
  {
    id: 'event-2',
    name: 'Another Event',
    startDate: '2026-11-15',
    endDate: '2026-11-15',
    cancelled: true
  },
  {
    id: 'event-3',
    name: 'New Event',
    startDate: '2026-11-20',
    endDate: '2026-11-21',
    cancelled: false
  }
];

console.log(compareEvents(previous, current));
