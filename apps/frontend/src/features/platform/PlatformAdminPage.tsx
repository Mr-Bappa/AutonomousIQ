import { useState, type CSSProperties } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/shared/api/client";
import { useAuth } from "@/shared/auth/AuthContext";

type Request = { id:string; company_name:string; contact_info:string; status:string };
type Tenant = { id:string; name:string };

export function PlatformAdminPage() {
  const { logout } = useAuth(); const qc = useQueryClient();
  const [credentials, setCredentials] = useState<{email:string,password:string}|null>(null);
  const requests = useQuery({ queryKey:["platform-requests"], queryFn:()=>apiRequest<Request[]>("/v1/tenant-requests") });
  const tenants = useQuery({ queryKey:["platform-tenants"], queryFn:()=>apiRequest<Tenant[]>("/v1/platform/tenants") });
  const approve = useMutation({ mutationFn:(id:string)=>apiRequest<{admin_email:string;temporary_password:string}>(`/v1/tenant-requests/${id}/approve`,{method:"POST"}), onSuccess:r=>{setCredentials({email:r.admin_email,password:r.temporary_password}); qc.invalidateQueries({queryKey:["platform-requests"]}); qc.invalidateQueries({queryKey:["platform-tenants"]});} });
  const reject = useMutation({ mutationFn:(id:string)=>apiRequest(`/v1/tenant-requests/${id}/reject`,{method:"POST"}), onSuccess:()=>qc.invalidateQueries({queryKey:["platform-requests"]}) });
  return <main style={{padding:32,maxWidth:1000,margin:"0 auto"}}>
    <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}><div><h1>AutonomousIQ Platform Admin</h1><p style={muted}>Global control plane · Super Admin</p></div><button style={button} onClick={logout}>Sign out</button></div>
    {credentials && <div style={card}><strong>Tenant provisioned.</strong> Admin: <code>{credentials.email}</code> · Temporary password: <code>{credentials.password}</code></div>}
    <section style={card}><h2>Pending tenant requests</h2>{requests.isLoading && <p>Loading…</p>}{requests.data?.filter(r=>r.status==="pending").map(r=><div key={r.id} style={row}><span><b>{r.company_name}</b> · {r.contact_info}</span><span><button style={secondary} onClick={()=>reject.mutate(r.id)}>Reject</button> <button style={button} onClick={()=>approve.mutate(r.id)}>Approve</button></span></div>)}{requests.data?.filter(r=>r.status==="pending").length===0 && <p style={muted}>No pending requests.</p>}</section>
    <section style={card}><h2>Tenants</h2>{tenants.data?.map(t=><div key={t.id} style={row}><b>{t.name}</b><code>{t.id}</code></div>)}{tenants.data?.length===0 && <p style={muted}>No tenants yet.</p>}</section>
  </main>;
}
const card:CSSProperties={border:"1px solid var(--color-border)",background:"var(--color-surface-raised)",borderRadius:8,padding:20,marginTop:20};
const row:CSSProperties={display:"flex",justifyContent:"space-between",alignItems:"center",padding:"12px 0",borderBottom:"1px solid var(--color-border)"};
const button:CSSProperties={padding:"8px 12px",border:0,borderRadius:6,background:"var(--color-accent)",color:"white",cursor:"pointer"};
const secondary:CSSProperties={...button,background:"transparent",color:"var(--color-text)",border:"1px solid var(--color-border)"};
const muted:CSSProperties={color:"var(--color-text-muted)"};
