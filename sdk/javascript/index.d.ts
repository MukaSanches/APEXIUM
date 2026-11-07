export type Row = Record<string, unknown>;
export type DataResult<T extends Row = Row> = {
  rows: T[];
  source: "openf1" | "jolpica";
  url: string;
  fetchedAt: string;
  cached: boolean;
  metadata: Record<string, unknown>;
};
export type FetchOptions = {
  fetcher?: typeof fetch;
  retries?: number;
  timeout?: number;
  minInterval?: number;
  ttl?: number;
  cache?: boolean;
  headers?: Record<string, string>;
};
export type QueryFilters = Record<string, string | number | boolean |
  readonly (string | number)[] | null | undefined>;
export type JolpicaOptions = {
  season?: string | number;
  round?: string | number;
  driver?: string;
  constructor?: string;
  limit?: number;
  offset?: number;
  ttl?: number;
};
export class ApexiumAPIError extends Error {
  readonly status: number;
  readonly url: string;
}
export class Transport {
  constructor(options?: FetchOptions);
  get(url: string, source: "openf1" | "jolpica", ttl?: number): Promise<DataResult>;
}
export class OpenF1 {
  constructor(transport: Transport, base?: string);
  query(endpoint: string, filters?: QueryFilters,
    options?: { ttl?: number }): Promise<DataResult>;
  meetings(filters?: QueryFilters): Promise<DataResult>;
  sessions(filters?: QueryFilters): Promise<DataResult>;
  drivers(filters?: QueryFilters): Promise<DataResult>;
  laps(filters?: QueryFilters): Promise<DataResult>;
  car_data(filters?: QueryFilters): Promise<DataResult>;
  pit(filters?: QueryFilters): Promise<DataResult>;
  stints(filters?: QueryFilters): Promise<DataResult>;
  overtakes(filters?: QueryFilters): Promise<DataResult>;
  position(filters?: QueryFilters): Promise<DataResult>;
  session_result(filters?: QueryFilters): Promise<DataResult>;
}
export class Jolpica {
  constructor(transport: Transport, base?: string);
  query(resource: string, options?: JolpicaOptions): Promise<DataResult>;
  allPages(resource: string, options?: JolpicaOptions & {
    pageSize?: number; maxPages?: number;
  }): Promise<DataResult>;
  results(options?: JolpicaOptions): Promise<DataResult>;
  races(options?: JolpicaOptions): Promise<DataResult>;
  driverstandings(options?: JolpicaOptions): Promise<DataResult>;
  constructorstandings(options?: JolpicaOptions): Promise<DataResult>;
  drivers(options?: JolpicaOptions): Promise<DataResult>;
  constructors(options?: JolpicaOptions): Promise<DataResult>;
}
export class Apexium {
  readonly openf1: OpenF1;
  readonly jolpica: Jolpica;
  constructor(options?: FetchOptions);
  race(year: number, grandPrix: string): Race;
}
export class Race {
  constructor(provider: OpenF1, year: number, grandPrix: string);
  meeting(): Promise<Row>;
  session(): Promise<Row>;
  query(resource: string, filters?: QueryFilters): Promise<DataResult>;
  results(filters?: QueryFilters): Promise<DataResult>;
  laps(filters?: QueryFilters): Promise<DataResult>;
  pits(filters?: QueryFilters): Promise<DataResult>;
  stints(filters?: QueryFilters): Promise<DataResult>;
  positions(filters?: QueryFilters): Promise<DataResult>;
  overtakes(filters?: QueryFilters): Promise<DataResult>;
  weather(filters?: QueryFilters): Promise<DataResult>;
  telemetry(filters?: QueryFilters): Promise<DataResult>;
}
export function racePace(laps: DataResult | Row[], minLaps?: number): Row[];
export function overtakeCounts(rows: DataResult | Row[]): Row[];
