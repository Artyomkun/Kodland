declare module 'corsbridge' {
    interface CorsFetchOptions {
        method?: string;
        headers?: Record<string, string>;
        body?: any;
        timeout?: number;
        mode?: 'cors' | 'no-cors' | 'same-origin';
        credentials?: 'include' | 'same-origin' | 'omit';
        cache?: 'default' | 'no-cache' | 'reload' | 'force-cache' | 'only-if-cached';
        redirect?: 'follow' | 'manual' | 'error';
        referrer?: string;
        referrerPolicy?: ReferrerPolicy;
        integrity?: string;
        keepalive?: boolean;
        signal?: AbortSignal;
    }
    export function corsFetch<T = any>(url: string, options?: CorsFetchOptions): Promise<T>;
}