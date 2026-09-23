const base=process.env.NEXT_PUBLIC_API_URL||"http://localhost:8000";
export async function api<T>(path:string, init?:RequestInit):Promise<T>{
 const r=await fetch(base+path,{...init,headers:{"content-type":"application/json","x-tenant-id":"00000000-0000-4000-8000-000000000001",...(init?.headers||{})},cache:"no-store"});
 if(!r.ok) throw new Error(`${r.status} ${await r.text()}`);
 return r.json() as Promise<T>;
}
