/* Real Chromium integration check; run via tests/run_browser.py. */
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const [url, mediaPath, artifacts, phase='main'] = process.argv.slice(2);
const checks=[];
async function poll(fn){const end=Date.now()+10000;while(Date.now()<end){if(await fn())return;await new Promise(r=>setTimeout(r,80));}throw new Error('Condition timed out');}
async function check(name, fn){await fn();checks.push(name);console.log('PASS '+name);}
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_EXECUTABLE || undefined});
 try {
  const context=await browser.newContext({viewport:{width:1440,height:1100}});
  const page=await context.newPage();
  const errors=[];page.on('pageerror',e=>errors.push(e.message));

  if(phase==='main'){
   // Generate our own moving test pattern, no private media or external downloads.
   const bytes=await page.evaluate(async()=>{
    const canvas=document.createElement('canvas');canvas.width=320;canvas.height=180;
    const ctx=canvas.getContext('2d');const chunks=[];
    const stream=canvas.captureStream(10);const recorder=new MediaRecorder(stream,{mimeType:'video/webm;codecs=vp8'});
    recorder.ondataavailable=e=>chunks.push(e.data);
    const finished=new Promise(resolve=>recorder.onstop=resolve);
    recorder.start();let frame=0;
    const timer=setInterval(()=>{ctx.fillStyle=frame++%2?'#366aa2':'#a26a36';ctx.fillRect(0,0,320,180);},100);
    await new Promise(resolve=>setTimeout(resolve,4200));recorder.stop();await finished;clearInterval(timer);stream.getTracks().forEach(t=>t.stop());
    return Array.from(new Uint8Array(await new Blob(chunks,{type:'video/webm'}).arrayBuffer()));
   });fs.writeFileSync(mediaPath,Buffer.from(bytes));
  }
  await page.goto(url);await page.waitForSelector('.channel-button');
  const api=(path)=>page.evaluate(async path=>{const r=await fetch(path);return r.json()},path);
  if(phase==='restart'){
   await check('settings survive server and browser restart',async()=>{
    assert.equal((await api('/api/users/user-1/settings')).settings.subtitles,'en');
    assert.equal(await page.locator('#subtitleSelect').inputValue(),'en');
   });
   await check('history survives server and browser restart',async()=>{
    assert((await api('/api/users/user-2/history')).length>0);
   });
  }else{
   await check('catalog loads through API, no JSON fallback',async()=>{
    assert.equal(await page.locator('.channel-button').count(),4);
    assert.equal(await page.locator('.recommendation').count(),4);
    assert.equal(await page.locator('script[src*="db.js"]').count(),0);
   });
   await check('startup does not create watching history',async()=>{
    assert.equal((await api('/api/users/user-1/history')).length,2);
    assert.equal((await api('/api/users/user-2/history')).length,0);
   });
   await check('settings saved in SQLite and restored on reload',async()=>{
    await page.selectOption('#subtitleSelect','en');
    await page.waitForFunction(()=>document.getElementById('persistenceStatus').textContent.includes('Settings saved'));
    assert.equal((await api('/api/users/user-1/settings')).settings.subtitles,'en');
    await page.reload();await page.waitForSelector('.channel-button');
    assert.equal(await page.locator('#subtitleSelect').inputValue(),'en');
   });
   await check('profile isolation and rapid setting changes',async()=>{
    await page.selectOption('#loginSelect','user-2');
    assert.equal(await page.locator('#subtitleSelect').inputValue(),'cs');
    await page.evaluate(()=>{
     const el=document.getElementById('subtitleSelect');
     for(const value of ['off','en','cs']){el.value=value;el.dispatchEvent(new Event('change'));}
    });
    await poll(async()=>{const d=await api('/api/users/user-2/settings');return d.revision===3 && d.settings.subtitles==='cs'});
    assert.equal((await api('/api/users/user-2/settings')).settings.subtitles,'cs');
    assert.equal((await api('/api/users/user-1/settings')).settings.subtitles,'en');
   });
   await check('real playback writes progress to the correct profile',async()=>{
    await page.locator('video').evaluate(v=>v.play());
    await page.waitForFunction(()=>document.querySelector('video').currentTime>1);
    await page.locator('video').evaluate(v=>v.pause());
    await poll(async()=> (await api('/api/users/user-2/history')).some(x=>x.watchedSeconds>0.8));
    assert.equal((await api('/api/users/user-1/history')).length,2);
   });
   await check('switching profile while playing flushes the old profile',async()=>{
    await page.locator('video').evaluate(v=>v.play());
    await page.waitForFunction(()=>document.querySelector('video').currentTime>1.8);
    await page.selectOption('#loginSelect','user-1');
    await poll(async()=> (await api('/api/users/user-2/history')).some(x=>x.watchedSeconds>1.7));
    assert.equal((await api('/api/users/user-1/history')).length,2);
   });
   await check('changing episode flushes old progress and completion is recorded',async()=>{
    await page.locator('video').evaluate(v=>v.play());
    await page.waitForFunction(()=>document.querySelector('video').currentTime>0.5);
    const oldEpisode=await page.evaluate(()=>state.currentEpisodeId);
    await page.locator('.show-card').nth(1).click();
    await poll(async()=> (await api('/api/users/user-1/history')).some(x=>x.episodeId===oldEpisode && x.watchedSeconds>0.4));
    const newEpisode=await page.evaluate(()=>state.currentEpisodeId);
    assert.notEqual(oldEpisode,newEpisode);
    await page.locator('video').evaluate(v=>v.play());
    await page.waitForFunction(()=>document.querySelector('video').ended);
    await poll(async()=> (await api('/api/users/user-1/history')).some(x=>x.episodeId===newEpisode && x.completed));
   });
   await check('late settings response does not change another profile UI',async()=>{
    await page.route('**/api/users/user-1/settings',async route=>{
     if(route.request().method()==='PATCH')await new Promise(r=>setTimeout(r,300));
     await route.continue();
    });
    await page.selectOption('#subtitleSelect','off');
    await page.selectOption('#loginSelect','user-2');
    await poll(async()=> (await api('/api/users/user-1/settings')).settings.subtitles==='off');
    assert.equal(await page.locator('#subtitleSelect').inputValue(),'cs');
    await page.unroute('**/api/users/user-1/settings');
    await page.selectOption('#loginSelect','user-1');
    await page.selectOption('#subtitleSelect','en');
    await poll(async()=> (await api('/api/users/user-1/settings')).settings.subtitles==='en');
   });
   await check('search remains functional',async()=>{
    await page.fill('#searchInput','no-match-123456');assert.equal(await page.locator('.show-card').count(),0);
    await page.fill('#searchInput','');assert((await page.locator('.show-card').count())>0);
   });
   await check('server write failure is visible and rolls UI back',async()=>{
    await page.route('**/api/users/user-1/settings',async route=>{
     if(route.request().method()==='PATCH')return route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({error:'Test unavailable'})});
     return route.continue();
    });
    await page.selectOption('#subtitleSelect','off');
    await page.waitForFunction(()=>document.getElementById('persistenceStatus').textContent.includes('not confirmed saved'));
    assert.equal(await page.locator('#subtitleSelect').inputValue(),'en');
    assert.equal((await api('/api/users/user-1/settings')).settings.subtitles,'en');
    await page.unroute('**/api/users/user-1/settings');
   });
   await check('one-time legacy import is explicit and skips modified profiles',async()=>{
    await page.evaluate(()=>localStorage.setItem('netvision-prototype-state',JSON.stringify({users:{'user-1':{settings:{subtitles:'off'}},'user-2':{settings:{subtitles:'en'}}}})));
    await page.reload();await page.waitForSelector('#importLegacy:visible');
    page.once('dialog',d=>d.accept());await page.click('#importLegacy');
    await page.waitForFunction(()=>document.getElementById('importLegacy').hidden);
    assert.equal((await api('/api/users/user-1/settings')).settings.subtitles,'en');
    assert.equal(await page.evaluate(()=>localStorage.getItem('netvision-prototype-state')),null);
    assert.equal((await api('/api/bootstrap')).legacyImportDone,true);
   });
   await page.screenshot({path:path.join(artifacts,'desktop.png')});
   await page.setViewportSize({width:390,height:844});
   await page.screenshot({path:path.join(artifacts,'mobile.png')});
   await page.locator('#subtitleSelect').scrollIntoViewIfNeeded();
   await page.screenshot({path:path.join(artifacts,'mobile-settings.png')});
   await page.locator('#searchInput').scrollIntoViewIfNeeded();
   await page.screenshot({path:path.join(artifacts,'mobile-catalog.png')});
   await check('mobile viewport has no horizontal overflow',async()=>assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth))); 
   await check('no uncaught JavaScript exceptions',async()=>assert.deepEqual(errors,[]));
  }
  fs.writeFileSync(path.join(artifacts,`browser-${phase}.json`),JSON.stringify({checks,browser:await browser.version()},null,2));
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
