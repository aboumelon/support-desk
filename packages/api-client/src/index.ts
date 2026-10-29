import createClient from 'openapi-fetch';
import type { paths } from './generated/http';
export type { components, paths } from './generated/http';
export const api = createClient<paths>({credentials: 'same-origin'});
