import test from "node:test";
import assert from "node:assert/strict";
import { Apexium, OpenF1, Jolpica, Transport, racePace, overtakeCounts }
  from "./index.js";

const json = (payload) => new Response(JSON.stringify(payload), { status: 200 });

test("OpenF1 URL, multi filters, range operators and provenance", async () => {
  let requested;
  const client = new OpenF1(new Transport({ minInterval: 0, fetcher: async (url) => {
    requested = new URL(url);
    return json([{ driver_number: 44 }]);
  }}));
  const result = await client.laps({ lap_duration__gte: 90, driver_number: [44, 1] });
  assert.equal(requested.pathname, "/v1/laps");
  assert.equal(requested.searchParams.get("lap_duration>"), "90");
  assert.deepEqual(requested.searchParams.getAll("driver_number"), ["44", "1"]);
  assert.equal(result.rows.length, 1);
  assert.equal(result.source, "openf1");
});

test("In-memory cache prevents duplicate remote requests", async () => {
  let requests = 0;
  const client = new OpenF1(new Transport({ minInterval: 0, fetcher: async () => {
    requests++;
    return json([]);
  }}));
  const one = await client.meetings({ year: 2025 });
  const two = await client.meetings({ year: 2025 });
  assert.equal(requests, 1);
  assert.equal(one.cached, false);
  assert.equal(two.cached, true);
});

test("Jolpica unwraps MRData and validates path", async () => {
  const api = new Jolpica(new Transport({ minInterval: 0, fetcher: async () =>
    json({ MRData: { total: "1", RaceTable: { Races: [{ round: "1" }] } } }) }));
  const result = await api.results({ season: 2025, round: 1 });
  assert.equal(result.rows[0].round, "1");
  await assert.rejects(api.query("invalid"), /Unknown Jolpica/);
  await assert.rejects(api.query("results", { season: "../test" }), /Invalid API path/);
});

test("Race resolves Brazil by official country and selects GP rather than Sprint", async () => {
  const fetcher = async (url) => {
    if (url.includes("/meetings")) return json([
      { meeting_key: 1, country_name: "Brazil", meeting_name: "São Paulo Grand Prix" }]);
    if (url.includes("/sessions")) return json([
      { session_key: 2, meeting_key: 1, session_name: "Sprint", session_type: "Race" },
      { session_key: 3, meeting_key: 1, session_name: "Race", session_type: "Race" }]);
    return json([{ driver_number: 44, position: 1 }]);
  };
  const race = new Apexium({ fetcher, minInterval: 0 }).race(2025, "Brazil");
  assert.equal((await race.session()).session_key, 3);
  assert.equal((await race.results()).rows[0].position, 1);
});

test("Analytics use recorded laps and overtakes", () => {
  const samples = [{ driver_number: 44, lap_duration: 92 },
    { driver_number: 44, lap_duration: 91 },
    { driver_number: 44, lap_duration: 90 }];
  assert.equal(racePace(samples)[0].median_seconds, 91);
  assert.equal(overtakeCounts([{ overtaking_driver_number: 44 }])[0]
    .recorded_position_swaps, 1);
});
