// Run only on the organiser's trusted machine. Never put PROXY_TOKEN in the browser.
const action=process.argv[2];
if(!['invite','feedback'].includes(action))throw new Error('Usage: node admin.mjs invite|feedback');
if(!process.env.PROXY_TOKEN)throw new Error('Configure PROXY_TOKEN in the trusted environment, not in source code.');
const endpoint=process.env.MAMA_API_URL || 'https://mama-helper-ai-proxy.reborntechsar.workers.dev';
const r=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json',Origin:'https://mama-helper-landing--preview.poehali.dev',Authorization:'Bearer '+process.env.PROXY_TOKEN},body:JSON.stringify({action:action==='invite'?'invite-create':'feedback-export',cursor:process.argv[3]})});
const body=await r.json();if(!r.ok)throw new Error(body.error || 'Request failed');
console.log(JSON.stringify(body,null,2));
