# APEXIUM JavaScript SDK

Zero dependency ESM client for **Node.js 18+ and modern browsers**. The source package is in this repository; it has not yet been published to npm.

~~~js
import { Apexium, racePace } from "./index.js";

const f1 = new Apexium();
const { rows: meetings } = await f1.openf1.meetings({ year: 2025 });
console.log(meetings.length);

const race = f1.race(2025, "Brazil");
const laps = await race.laps({ driver_number: 44 });
console.log(racePace(laps));
~~~

Methods named after every documented OpenF1 endpoint are available. Generic calls can use f1.openf1.query("laps", {session_key: 9165}).

Historical Jolpica example:

~~~js
const standings = await f1.jolpica.driverstandings({ season: 2025 });
console.log(standings.rows[0]?.DriverStandings);
~~~

The SDK returns objects with rows, source, url, fetchedAt, cached, and metadata. It does not store live data or bypass upstream rate limits. Browser CORS behavior is controlled by the source API.

Run tests with: npm test
