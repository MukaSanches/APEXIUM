/**
 * APEXIUM JavaScript SDK. Fetch, retry, query & provenance without dependencies.
 * Browser/Node 18+ with native fetch. Uses real upstream APIs, not invented data.
 */
const OPENF1_ENDPOINTS = new Set([
  "car_data", "championship_drivers", "championship_teams", "drivers",
  "intervals", "laps", "location", "meetings", "overtakes", "pit", "position",
  "race_control", "sessions", "session_result", "starting_grid", "stints",
  "team_radio", "weather",
]);
const JOLPICA_RESOURCES = new Set([
  "races", "results", "qualifying", "sprint", "drivers", "constructors",
  "circuits", "seasons", "status", "driverstandings", "constructorstandings",
  "laps", "pitstops",
]);
const OPS = { eq: "=", gt: ">", gte: ">=", lt: "<", lte: "<=" };
const clean = (value) => String(value).normalize("NFKD")
  .replace(/[\u0300-\u036f]/g, "").toLowerCase();
const safe = (part) => {
  const text = String(part);
  if (!/^[A-Za-z0-9_-]+$/.test(text)) throw new Error("Invalid API path component");
  return text;
};
const pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export class ApexiumAPIError extends Error {
  constructor(status, url, details = "") {
    super("HTTP " + status + ": " + details.slice(0, 200) + " (" + url + ")");
    this.status = status;
    this.url = url;
    this.name = "ApexiumAPIError";
  }
}

export class Transport {
  constructor({ fetcher = globalThis.fetch, retries = 2, timeout = 20000,
                 minInterval = 350, ttl = 21600000, cache = true, headers = {} } = {}) {
    if (typeof fetcher !== "function") throw new TypeError("fetch is unavailable");
    if (retries < 0 || timeout <= 0 || minInterval < 0 || ttl < 0) {
      throw new RangeError("Invalid transport configuration");
    }
    this.fetcher = fetcher;
    this.retries = retries;
    this.timeout = timeout;
    this.minInterval = minInterval;
    this.ttl = ttl;
    this.headers = { Accept: "application/json", ...headers };
    this.cache = cache ? new Map() : null;
    this.nextSlot = 0;
  }

  async get(url, source, customTtl = this.ttl) {
    const now = Date.now();
    const item = this.cache?.get(url);
    if (item && item.expires > now && customTtl > 0) {
      return { rows: item.rows, source, url, fetchedAt: item.fetchedAt, cached: true,
               metadata: item.metadata };
    }
    for (let attempt = 0; attempt <= this.retries; attempt++) {
      const slot = Math.max(Date.now(), this.nextSlot);
      this.nextSlot = slot + this.minInterval;
      if (slot > Date.now()) await pause(slot - Date.now());
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.timeout);
      let response;
      try {
        response = await this.fetcher(url, { headers: this.headers, signal: controller.signal });
      } catch (error) {
        if (attempt === this.retries) throw error;
        await pause(Math.min(2 ** attempt * 1000, 8000));
        continue;
      } finally {
        clearTimeout(timeoutId);
      }
      if (!response.ok) {
        const details = await response.text();
        if (![429, 500, 502, 503, 504].includes(response.status) || attempt === this.retries) {
          throw new ApexiumAPIError(response.status, url, details);
        }
        const raw = response.headers?.get?.("Retry-After");
        const numeric = Number(raw);
        const delay = raw && Number.isFinite(numeric) ? Math.min(numeric * 1000, 30000)
          : Math.min(2 ** attempt * 1000, 8000);
        await pause(delay);
        continue;
      }
      const payload = await response.json();
      let rows, metadata = {};
      if (source === "openf1") {
        if (!Array.isArray(payload)) throw new TypeError("Unexpected OpenF1 JSON shape");
        rows = payload;
      } else {
        if (!payload?.MRData) throw new TypeError("Unexpected Jolpica JSON shape");
        const mr = payload.MRData;
        const table = Object.values(mr).find((value) => value && typeof value === "object"
          && !Array.isArray(value) && Object.keys(value).some((key) =>
            ["Races", "StandingsLists", "Drivers", "Constructors", "Circuits",
             "Seasons", "Status"].includes(key)));
        rows = table ? (["Races", "StandingsLists", "Drivers", "Constructors", "Circuits",
          "Seasons", "Status"].map((key) => table[key]).find(Array.isArray) ?? []) : [];
        metadata = { limit: mr.limit, offset: mr.offset, total: mr.total, series: mr.series };
      }
      if (!rows.every((row) => row && typeof row === "object" && !Array.isArray(row))) {
        throw new TypeError("Unexpected API record structure");
      }
      const fetchedAt = new Date().toISOString();
      if (this.cache && customTtl > 0) {
        this.cache.set(url, { rows, expires: Date.now() + customTtl, fetchedAt, metadata });
      }
      return { rows, source, url, fetchedAt, cached: false, metadata };
    }
    throw new Error("Unreachable retry state");
  }
}

export class OpenF1 {
  constructor(transport, base = "https://api.openf1.org/v1") {
    this.transport = transport;
    this.base = base.replace(/\/$/, "");
  }

  async query(endpoint, filters = {}, options = {}) {
    if (!OPENF1_ENDPOINTS.has(endpoint)) throw new RangeError("Unknown OpenF1 endpoint");
    const params = new URLSearchParams();
    for (let [key, value] of Object.entries(filters)) {
      const parts = key.split("__");
      if (parts.length === 2 && OPS[parts[1]]) key = parts[0] + OPS[parts[1]];
      if (!/^[A-Za-z0-9_><=]+$/.test(key)) throw new RangeError("Invalid filter");
      if (value == null) continue;
      for (const entry of Array.isArray(value) ? value : [value]) params.append(key, String(entry));
    }
    params.sort();
    const suffix = params.toString();
    const url = this.base + "/" + endpoint + (suffix ? "?" + suffix : "");
    const latest = Object.values(filters).some((v) => v === "latest");
    return this.transport.get(url, "openf1", options.ttl ?? (latest ? 10000 : 21600000));
  }
}
for (const name of OPENF1_ENDPOINTS) {
  Object.defineProperty(OpenF1.prototype, name, {
    value: function (filters = {}, options = {}) { return this.query(name, filters, options); },
  });
}

export class Jolpica {
  constructor(transport, base = "https://api.jolpi.ca/ergast/f1") {
    this.transport = transport;
    this.base = base.replace(/\/$/, "");
  }

  async query(resource, options = {}) {
    if (!JOLPICA_RESOURCES.has(resource)) throw new RangeError("Unknown Jolpica resource");
    const { season, round, driver, constructor, limit = 100, offset = 0, ttl } = options;
    if (!Number.isInteger(limit) || limit < 1 || limit > 2000 ||
        !Number.isInteger(offset) || offset < 0) throw new RangeError("Invalid pagination");
    if (round != null && season == null) throw new RangeError("round requires season");
    const path = [];
    if (season != null) path.push(safe(season));
    if (round != null) path.push(safe(round));
    if (driver != null) path.push("drivers", safe(driver));
    if (constructor != null) path.push("constructors", safe(constructor));
    path.push(resource + ".json");
    const url = this.base + "/" + path.join("/") +
      "?" + new URLSearchParams({ limit: String(limit), offset: String(offset) });
    return this.transport.get(url, "jolpica", ttl);
  }

  async allPages(resource, { pageSize = 100, maxPages = 10, ...opts } = {}) {
    if (maxPages < 1) throw new RangeError("maxPages must be positive");
    let offset = opts.offset ?? 0;
    const rows = [];
    let first;
    for (let page = 0; page < maxPages; page++) {
      const data = await this.query(resource, { ...opts, limit: pageSize, offset });
      first ??= data;
      rows.push(...data.rows);
      offset += data.rows.length;
      const total = Number(data.metadata.total || 0);
      if (data.rows.length === 0 || (total && offset >= total)) break;
    }
    return { ...first, rows, metadata: { ...first.metadata, returned: rows.length,
                                        nextOffset: offset } };
  }
}
for (const name of JOLPICA_RESOURCES) {
  Object.defineProperty(Jolpica.prototype, name, {
    value: function (options = {}) { return this.query(name, options); },
  });
}

export class Apexium {
  constructor(options = {}) {
    this.openf1 = new OpenF1(new Transport({ ...options, minInterval: options.minInterval ?? 360 }));
    this.jolpica = new Jolpica(new Transport({ ...options, minInterval: options.minInterval ?? 260 }));
  }

  race(year, grandPrix) {
    if (!Number.isInteger(year) || year < 2023) {
      throw new RangeError("OpenF1 race context supports 2023 onward");
    }
    if (!grandPrix?.trim()) throw new RangeError("Provide a Grand Prix name");
    return new Race(this.openf1, year, grandPrix);
  }
}

export class Race {
  constructor(provider, year, grandPrix) {
    this.provider = provider;
    this.year = year;
    this.grandPrix = grandPrix;
    this.meetingPromise = null;
    this.sessionPromise = null;
  }

  async meeting() {
    this.meetingPromise ??= (async () => {
      const { rows } = await this.provider.meetings({ year: this.year });
      const match = (row, exact) => ["meeting_name", "country_name", "location",
        "circuit_short_name"].some((field) => exact
          ? clean(row[field] ?? "") === clean(this.grandPrix)
          : clean(row[field] ?? "").includes(clean(this.grandPrix)));
      const exact = rows.filter((row) => match(row, true));
      const found = exact.length ? exact : rows.filter((row) => match(row, false));
      if (found.length !== 1) throw new Error("Grand Prix missing or ambiguous");
      return found[0];
    })();
    return this.meetingPromise;
  }

  async session() {
    this.sessionPromise ??= (async () => {
      const meeting = await this.meeting();
      const { rows } = await this.provider.sessions({ meeting_key: meeting.meeting_key });
      const found = rows.find((row) => row.session_name === "Race") ??
        rows.find((row) => row.session_type === "Race" &&
          !String(row.session_name).includes("Sprint"));
      if (!found) throw new Error("Race session not available");
      return found;
    })();
    return this.sessionPromise;
  }

  async query(resource, filters = {}) {
    const session = await this.session();
    return this.provider.query(resource, { session_key: session.session_key, ...filters });
  }
}
const raceRoutes = {
  results: "session_result", laps: "laps", drivers: "drivers", pits: "pit",
  stints: "stints", positions: "position", overtakes: "overtakes",
  telemetry: "car_data", location: "location", weather: "weather",
  radio: "team_radio", raceControl: "race_control", startingGrid: "starting_grid",
  intervals: "intervals",
};
for (const [method, route] of Object.entries(raceRoutes)) {
  Object.defineProperty(Race.prototype, method, {
    value: function (filters = {}) { return this.query(route, filters); },
  });
}

/** Observed lap statistics; not normalized for compound, weather, fuel or traffic. */
export function racePace(laps, minLaps = 3) {
  if (minLaps < 1) throw new RangeError("minLaps must be positive");
  const grouped = new Map();
  for (const lap of Array.isArray(laps) ? laps : laps.rows) {
    if (typeof lap.lap_duration !== "number" || lap.lap_duration <= 0 ||
        lap.is_pit_out_lap || lap.driver_number == null) continue;
    const samples = grouped.get(lap.driver_number) ?? [];
    samples.push(lap.lap_duration);
    grouped.set(lap.driver_number, samples);
  }
  return [...grouped].filter(([, arr]) => arr.length >= minLaps)
    .map(([driver_number, arr]) => {
      arr.sort((a, b) => a - b);
      const n = arr.length;
      const median_seconds = n % 2 ? arr[(n - 1) / 2] :
        (arr[n / 2 - 1] + arr[n / 2]) / 2;
      return { driver_number, lap_count: n, median_seconds,
               mean_seconds: arr.reduce((a, b) => a + b, 0) / n,
               best_seconds: arr[0] };
    }).sort((a, b) => a.median_seconds - b.median_seconds);
}

/** Counts all recorded position swaps, including pits/penalties in upstream feed. */
export function overtakeCounts(rows) {
  const counts = new Map();
  for (const row of Array.isArray(rows) ? rows : rows.rows) {
    const driver = row.overtaking_driver_number;
    if (driver != null) counts.set(driver, (counts.get(driver) ?? 0) + 1);
  }
  return [...counts].map(([driver_number, recorded_position_swaps]) =>
    ({ driver_number, recorded_position_swaps }))
    .sort((a, b) => b.recorded_position_swaps - a.recorded_position_swaps);
}
