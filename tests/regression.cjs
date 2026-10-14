const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const root=path.resolve(__dirname,'..');
const source=fs.readFileSync(path.join(root,'app.js'),'utf8').split('init().catch')[0];
const ctx=vm.createContext({document:{getElementById:()=>({})},Date});vm.runInContext(source,ctx);
ctx.data=JSON.parse(fs.readFileSync(path.join(root,'data/db.json')));
const actual=vm.runInContext(`state.db=data; ({profiles: data.users.map(u=>{state.db.currentUserId=u.id; return {id:u.id,scores:data.programs.map(p=>[p.id,scoreProgram(p)]),available:data.channels.map(c=>[c.id,isChannelAvailable(c)])}}), bundles:data.episodes.map(e=>{const b=episodeBundle(e.id);return [e.id,b.program.id,b.channel.id,b.media.id]}),firstEpisodes:data.channels.map(c=>[c.id,firstPlayableEpisode(c.id)?.id]), schedule: ['2026-10-12T05:59:00','2026-10-12T06:00:00','2026-10-12T09:00:00','2026-10-17T18:30:00'].map(t=>[t,data.scheduleItems.map(s=>isScheduleLive(s,new Date(t)))])})`,ctx);
assert.deepEqual(JSON.parse(JSON.stringify(actual)),JSON.parse(fs.readFileSync(path.join(__dirname,'fixtures/original-behavior.json'))));
console.log('PASS original scores, region availability, 23 episode relations, default episode order and schedule boundaries');
