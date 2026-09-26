from pathlib import Path
from html import escape
import subprocess

ROOT = Path(__file__).parent
SCENES = [
    ("01", 0, 9), ("02", 9, 14), ("03", 23, 11), ("04", 34, 12),
    ("05", 46, 12), ("06", 58, 14), ("07", 72, 12), ("08", 84, 12),
    ("09", 96, 8), ("10", 104, 8),
]

def header(n, kicker, title, sub=""):
    return f'<div class="head"><div class="kicker appear">{n} / {kicker}</div><h1 class="appear">{title}</h1><p class="appear">{sub}</p></div>'

def svg_antenna():
    return '''<svg class="antenna" viewBox="0 0 250 310" aria-label="Illustrated wideband receiving antenna">
<defs><linearGradient id="metal" x2="1" y2="1"><stop stop-color="#d4deee"/><stop offset=".45" stop-color="#627b99"/><stop offset="1" stop-color="#d6e3f1"/></linearGradient></defs>
<path d="M122 255 L122 88 M72 94 L172 94 M87 126 L157 126 M106 255 L140 255 M73 270 L174 270" stroke="url(#metal)" stroke-width="9" fill="none" stroke-linecap="round"/>
<path d="M122 89 L68 37 M122 89 L176 37" stroke="url(#metal)" stroke-width="7" fill="none" stroke-linecap="round"/>
<circle cx="122" cy="82" r="10" fill="#55d9ef"/><path d="M39 49 Q122 -35 205 49 M54 67 Q122 -3 190 67" stroke="#55d9ef" stroke-width="3" fill="none" opacity=".8"/>
<rect x="82" y="266" width="82" height="18" rx="5" fill="#667993"/></svg>'''

def box(label, detail, icon):
    return f'<div class="hwbox appear"><div class="hwicon">{icon}</div><strong>{label}</strong><small>{detail}</small></div>'

hw = (
    box("RF FRONT END", "filters + gain", "⌁") +
    '<div class="wire"></div>' +
    box("TUNER", "selects a slice", "◉") +
    '<div class="wire"></div>' +
    box("ADC", "samples the slice", "▥") +
    '<div class="wire"></div>' +
    box("COMPUTE", "scores each scan", "▣")
)

def bands(prefix):
    return ''.join(f'<div class="band" id="{prefix}{i}"><span>{i:02}</span></div>' for i in range(1,17))

sc = {}
sc['01'] = header('01','CONTINUING THE PROBLEM','The signal was there.','The receiver reached its frequency too late.') + '''
<div class="spectrum wide appear"><div class="axis"><span>FREQUENCY →</span><span>16 POSSIBLE BANDS</span></div><div class="bands">'''+bands('a')+'''</div><div class="aperture" id="ap1"></div><div class="burst" id="burst1"></div></div>
<div class="prompt appear">Where should the receiver listen next?</div>'''

sc['02'] = header('02','PHYSICAL LIMIT','The hardware sets the window.','A wide environment enters a narrow instantaneous receiver path.') + f'''
<div class="hardware"><div class="antenna-wrap appear">{svg_antenna()}<div class="hwlabel">ANTENNA<br><em>wide RF environment</em></div></div><div class="feedline"></div><div class="hwchain">{hw}</div></div>
<div class="capacity appear"><div class="cap-top"><span>SIMULATED SPECTRUM</span><b>16 BANDS</b></div><div class="cap-band">{''.join('<i></i>' for _ in range(16))}</div><div class="cap-window">INSTANTANEOUS VIEW <b>2 ADJACENT BANDS</b></div><div class="cap-note">PROBLEM STATEMENT: TYPICALLY ≥10× NARROWER  ·  PROJECT SIMULATION: 2 OF 16 BANDS</div></div>'''

sc['03'] = header('03','THE CONSEQUENCE','A narrow window must move.','The next tuning decision changes which burst can be seen.') + '''
<div class="instrument appear"><div class="inst-top"><span>RF SPECTRUM</span><span>OBSERVATION APERTURE = 2 BANDS</span></div><div class="bands">'''+bands('b')+'''</div><div class="scan-window" id="scanWindow"></div><div class="pulse p1" id="pulse1"></div><div class="pulse p2" id="pulse2"></div><div class="pulse p3" id="pulse3"></div><div class="inst-foot"><span>RECEIVER TUNED HERE</span><span>SHORT RF BURST ELSEWHERE</span></div></div>
<div class="rule appear">SOFTWARE CANNOT WIDEN THE FRONT END. <b>IT CAN CHOOSE THE NEXT SCAN.</b></div>'''

sc['04'] = header('04','CLOSED LOOP','Make every scan count.','One receiver budget. Different decisions about its next frequency.') + '''
<div class="loop appear"><div class="loopbox"><div class="num">01</div><div class="glyph">◉</div><strong>OBSERVE</strong><small>listen to the current band pair</small></div><div class="arrow">→</div><div class="loopbox"><div class="num">02</div><div class="glyph">▥</div><strong>UPDATE</strong><small>band history and timing belief</small></div><div class="arrow">→</div><div class="loopbox focus"><div class="num">03</div><div class="glyph">◆</div><strong>CHOOSE</strong><small>select the next band pair</small></div><div class="arrow">→</div><div class="loopbox"><div class="num">04</div><div class="glyph">↗</div><strong>RETUNE</strong><small>repeat within the same hardware limit</small></div></div>
<div class="baseline appear">REFERENCE: <b>ROUND-ROBIN</b> visits each band pair in a fixed cycle and ignores feedback.</div>'''

sc['05'] = header('05','DESIGNED STRATEGIES','Two rules built for coverage.','Both are calculated policies; neither is a neural network.') + '''
<div class="two-models"><div class="model-box appear"><div class="model-top"><b>CTMC</b><span>RANDOMISED FLOOR</span></div><div class="model-graphic ctmc">◌ <i>→</i> ◉ <i>→</i> ◌ <i>→</i> ◉</div><p>Keeps a chance of visiting every band, breaking rigid timing patterns.</p></div><div class="model-box appear"><div class="model-top"><b>INDEX</b><span>BELIEF + REVISIT</span></div><div class="mini-rank"><div style="--w:88%">BAND 03 <i></i></div><div style="--w:68%">BAND 11 <i></i></div><div style="--w:51%">BAND 07 <i></i></div></div><p>Ranks likely activity while protecting time to revisit neglected bands.</p></div></div>
<div class="tiny-label appear">SAME RECEIVER • SAME BUDGET • DIFFERENT SCHEDULING RULES</div>'''

sc['06'] = header('06','LEARNED STRATEGIES','Four ways to learn where to look.','Reward from previous observations changes the next choice.') + '''
<div class="learning-grid"><div class="learn-card appear"><b>BANDIT</b><div class="mechanic">try ↔ exploit</div><p>Balances promising bands with exploration.</p></div><div class="learn-card appear"><b>Q-LEARNING</b><div class="mechanic">state → value table</div><p>Stores which action paid off in each state.</p></div><div class="learn-card appear"><b>DQN</b><div class="mechanic">state → neural Q</div><p>Uses a network to estimate action values.</p></div><div class="learn-card appear"><b>PPO</b><div class="mechanic">feedback → policy</div><p>Improves a probability-based scan policy.</p></div></div>'''

sc['07'] = header('07','DATA + VALIDATION','Two inputs. One virtual receiver.','Model registry records synthetic scenarios and Turing-replay runs.') + '''
<div class="data-flow"><div class="data-source appear"><div class="datasym">⌁</div><b>GENERATED SCENARIOS</b><p>fixed, periodic, agile and intermittent emitters</p></div><div class="merge-line">⟶</div><div class="data-source appear"><div class="datasym">▥</div><b>ALAN TURING REPLAY</b><p>synthetic radar pulses binned by time and frequency</p></div></div><div class="data-destination appear">↓ <b>VIRTUAL RECEIVER</b> ↓<br><span>identical observation and scoring pipeline</span></div>
<div class="scope appear">RECORDED EXPERIMENTS • SIMULATION ONLY • NO FIELD RF HARDWARE</div>'''

sc['08'] = header('08','MEASURED SCENARIO B','More active opportunities detected.','Held-out synthetic Scenario B • Index and baseline: six seeds, 2,000 steps.') + '''
<div class="metric-title appear">DETECTION PROBABILITY <span>Pd</span></div><div class="chart"><div class="bar-row appear"><div class="bar-label">FIXED SWEEP</div><div class="bar-track"><div class="bar base" style="--bar:54.6%"></div></div><div class="bar-val">0.1092</div></div><div class="bar-row appear"><div class="bar-label">INDEX</div><div class="bar-track"><div class="bar index" style="--bar:66.7%"></div></div><div class="bar-val">0.1334</div></div></div><div class="lift appear">+22% <span>relative to the fixed sweep</span></div>
<div class="source appear">Source: Ai-ml-1-Scheduler-Engine/IMPLEMENTATION.md, Scenario B holdout table</div>'''

sc['09'] = header('09','MEASURED SCENARIO B','Coverage was preserved.','Distinct emitters intercepted at least once.') + '''
<div class="coverage"><div class="cover-card appear"><span>FIXED SWEEP</span><strong>0.9667</strong><div class="covertrack"><div style="width:96.67%"></div></div></div><div class="equal appear">=</div><div class="cover-card gold appear"><span>INDEX</span><strong>0.9667</strong><div class="covertrack"><div style="width:96.67%"></div></div></div></div><div class="trade appear">Tradeoff: Bandit raised Pd to 0.3375, but its emitter coverage was 0.7100 in the reported comparison.</div>'''

sc['10'] = header('10','THE TAKEAWAY','A better decision, every scan.','The receiver stays narrow. The schedule uses its time more deliberately.') + '''
<div class="close-line appear"><span>TRAINING WALL TIME</span><b>NOT RECORDED COMPARABLY</b></div><div class="close-line appear"><span>SCHEDULER API LATENCY</span><b>6.6 ms p95, warm path</b></div><div class="mark appear">PUSHPAK <i>• SIMULATION ONLY</i></div>'''

css = r'''
@font-face{font-family:Archivo;src:url('assets/fonts/archivo-latin-var.woff2') format('woff2');font-weight:100 900}
@font-face{font-family:JetBrains;src:url('assets/fonts/jetbrains-mono-latin-var.woff2') format('woff2');font-weight:100 900}
*{box-sizing:border-box}html,body{margin:0;width:1920px;height:1080px;overflow:hidden;background:#06101c;color:#edf5fa;font-family:Archivo,Arial,sans-serif}#root{width:1920px;height:1080px;position:relative;overflow:hidden;background:radial-gradient(circle at 76% 18%,#10253a,#06101c 58%)}.clip{position:absolute;inset:0;width:100%;height:100%;overflow:hidden}.scene{position:absolute;inset:0;padding:66px 100px 72px;background:linear-gradient(120deg,rgba(9,25,42,.97),rgba(5,14,27,.98));overflow:hidden}.scene:before{content:'';position:absolute;inset:0;background:linear-gradient(90deg,transparent 0 96%,rgba(109,192,209,.05) 96% 97%,transparent 97%),linear-gradient(0deg,transparent 0 94%,rgba(109,192,209,.045) 94% 95%,transparent 95%);background-size:86px 86px;opacity:.25}.scene>*{position:relative}.head{height:205px}.kicker{font:700 22px JetBrains,monospace;letter-spacing:3px;color:#5fe0e9;margin-bottom:24px}.head h1{font-size:66px;line-height:1.04;letter-spacing:-2.4px;margin:0;font-weight:800;max-width:1450px}.head p{font-size:29px;color:#a7b9c9;margin:15px 0 0;max-width:1500px}.spectrum,.instrument{border:2px solid #4b738c;background:#071928;border-radius:14px;box-shadow:0 30px 75px #0007;position:relative}.wide{height:380px;margin-top:45px;padding:45px 45px}.axis,.inst-top,.inst-foot{display:flex;justify-content:space-between;color:#91b0c1;font:700 22px JetBrains,monospace;letter-spacing:1px}.bands{display:flex;gap:5px;height:170px;margin-top:44px}.band{flex:1;background:#172d42;border:1px solid #54758b;position:relative;overflow:hidden}.band span{position:absolute;bottom:10px;left:0;right:0;text-align:center;font:700 19px JetBrains;color:#a8bdca}.band:before{content:'';position:absolute;left:50%;height:100%;width:2px;background:#37607a;opacity:.45}.aperture,.scan-window{position:absolute;top:108px;height:176px;width:10.9%;border:6px solid #5de0ec;background:#5de0ec22;box-shadow:0 0 30px #45d2e255;left:17%}.burst,.pulse{position:absolute;width:30px;height:175px;background:#ff695a;box-shadow:0 0 18px #ff695a,0 0 55px #ff695a;top:109px;left:70%;opacity:0}.prompt{font-size:43px;font-weight:800;margin-top:70px;color:#f7c778}.hardware{display:flex;align-items:center;margin:18px 0;height:400px}.antenna-wrap{width:270px;text-align:center}.antenna{height:245px;width:230px}.hwlabel{font:700 23px JetBrains;color:#e5edf6}.hwlabel em{font:400 18px Archivo;color:#9eb3c3}.feedline{height:5px;width:80px;background:#4bcbdc}.hwchain{display:flex;align-items:center;flex:1}.hwbox{height:180px;min-width:230px;flex:1;border:2px solid #6387a0;background:linear-gradient(145deg,#20374a,#0d2439);border-radius:15px;padding:20px;display:flex;flex-direction:column;align-items:center;justify-content:center;box-shadow:inset 0 2px 14px #7ccde81b,0 15px 36px #0006}.hwbox strong{font:800 23px JetBrains;letter-spacing:1px}.hwbox small{color:#9ab6c7;font-size:19px;margin-top:7px}.hwicon{font-size:62px;color:#57daeb;margin-bottom:8px}.wire{height:5px;width:45px;background:#4bcbdc;flex:none}.capacity{margin-top:6px;width:100%;border:1px solid #4a748c;background:#0b2033;border-radius:13px;padding:18px 26px}.cap-top{display:flex;justify-content:space-between;font:700 21px JetBrains;color:#b1cad8}.cap-top b{color:#fff}.cap-band{display:flex;gap:5px;margin:18px 0 10px;height:28px}.cap-band i{flex:1;background:#2c6684;border-radius:3px}.cap-band i:nth-child(6),.cap-band i:nth-child(7){background:#efbd62;box-shadow:0 0 16px #f8b864}.cap-window{font:700 21px JetBrains;color:#ffd182}.cap-window b{margin-left:22px}.cap-note{font-size:16px;color:#8fa6b5;margin-top:8px}.instrument{height:465px;margin-top:40px;padding:44px}.instrument .bands{height:216px;margin-top:46px}.instrument .scan-window{top:120px;left:3.1%;height:221px}.instrument .pulse{top:120px;height:221px}.instrument .p1{left:65%}.instrument .p2{left:85%}.instrument .p3{left:39%}.inst-foot{font-size:19px;margin-top:24px}.rule{font:700 28px JetBrains;margin-top:44px;color:#c5d8e3}.rule b{color:#ffd282}.loop{display:flex;align-items:center;gap:13px;margin-top:70px}.loopbox{height:380px;flex:1;border:2px solid #5d8199;border-radius:18px;background:#122b3e;padding:26px;display:flex;flex-direction:column}.loopbox.focus{border-color:#f4bd5e;background:#2d2c2c}.loopbox .num{color:#66ddea;font:700 24px JetBrains}.loopbox .glyph{font-size:94px;color:#6de3ee;margin:16px 0}.loopbox strong{font-size:34px}.loopbox small{font-size:22px;color:#a4bdcc;margin-top:16px;line-height:1.35}.arrow{font-size:53px;color:#ecbc72}.baseline{font:500 25px JetBrains;margin-top:50px;color:#9fb7c7}.baseline b{color:#fff}.two-models{display:flex;gap:32px;margin-top:40px}.model-box{flex:1;height:470px;border:2px solid #46778d;border-radius:19px;background:#0e2b3a;padding:40px}.model-box:nth-child(2){border-color:#b89453;background:#202b34}.model-top{display:flex;align-items:baseline;justify-content:space-between}.model-top b{font-size:55px}.model-top span{font:700 20px JetBrains;color:#6de0e7}.model-box p{font-size:27px;color:#b8cad6;line-height:1.3;margin:28px 0}.model-graphic{font-size:70px;color:#6de0e7;letter-spacing:12px;text-align:center;padding:42px 0}.model-graphic i{font-size:45px;color:#efc06e;font-style:normal}.mini-rank{margin-top:40px}.mini-rank div{position:relative;font:700 20px JetBrains;margin:15px 0;padding:13px 18px;background:#193a4b;border-radius:6px;overflow:hidden}.mini-rank div i{position:absolute;left:0;bottom:0;width:var(--w);height:5px;background:#efbf6a}.tiny-label{font:700 22px JetBrains;letter-spacing:2px;color:#9db2bf;text-align:center;margin-top:35px}.learning-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:22px;margin-top:75px}.learn-card{height:470px;border:2px solid #46778d;border-radius:17px;background:linear-gradient(155deg,#163a4b,#0a1c2c);padding:34px 24px}.learn-card:nth-child(2n){border-color:#99814e}.learn-card b{font-size:35px;letter-spacing:-1px}.mechanic{font:700 21px JetBrains;color:#6ae0e9;margin:86px 0 48px;padding:16px 0;border-bottom:1px solid #48657b}.learn-card p{font-size:25px;line-height:1.3;color:#bdd0db}.data-flow{display:flex;align-items:center;gap:50px;margin-top:62px}.data-source{flex:1;height:305px;border:2px solid #547f94;border-radius:17px;background:#112f40;padding:30px}.data-source:nth-child(3){border-color:#bd9b59}.datasym{font-size:65px;color:#64dce8}.data-source b{font-size:29px}.data-source p{font-size:24px;color:#b5c7d3}.merge-line{font-size:65px;color:#e5bf77}.data-destination{text-align:center;margin-top:30px;font:700 30px JetBrains;color:#ffd182}.data-destination span{font:400 23px Archivo;color:#afc5d0}.scope{text-align:center;font:700 20px JetBrains;color:#8ea5b5;margin-top:32px}.metric-title{font:700 29px JetBrains;color:#e2f7fb;margin-top:45px}.metric-title span{color:#67dbe6}.chart{margin:45px 0 0;width:100%}.bar-row{display:flex;align-items:center;gap:25px;margin:40px 0}.bar-label{width:255px;font:700 25px JetBrains}.bar-track{height:92px;flex:1;background:#183144;border:1px solid #516f84;border-radius:8px;overflow:hidden}.bar{height:100%;width:var(--bar);transform-origin:left center}.bar.base{background:#52718a}.bar.index{background:linear-gradient(90deg,#46b8c7,#ffd177)}.bar-val{width:150px;font:800 33px JetBrains;text-align:right}.lift{font-size:85px;font-weight:900;color:#f4c775;margin-top:0}.lift span{font-size:30px;color:#d2e3e9}.source{font:500 18px JetBrains;color:#7896a8;margin-top:28px}.coverage{display:flex;align-items:center;gap:36px;margin-top:90px}.cover-card{border:2px solid #5c8298;background:#122c3e;border-radius:16px;flex:1;padding:30px 36px;height:310px}.cover-card.gold{border-color:#d0a759}.cover-card span{font:700 26px JetBrains}.cover-card strong{display:block;font:800 85px JetBrains;margin-top:30px}.covertrack{height:20px;background:#244455;border-radius:10px;margin-top:24px}.covertrack div{height:100%;background:#6ed7e3;border-radius:10px}.gold .covertrack div{background:#ebbf72}.equal{font-size:85px;color:#e4bf7a}.trade{font-size:27px;color:#b4c7d3;margin-top:58px}.close-line{display:flex;justify-content:space-between;width:100%;border-bottom:2px solid #426278;padding:25px 0;margin-top:30px;font:700 27px JetBrains}.close-line span{color:#9db9c8}.close-line b{color:#f6c874}.mark{font-size:62px;font-weight:900;letter-spacing:7px;color:#f5c66c;margin-top:74px}.mark i{font:700 20px JetBrains;color:#91aeba;letter-spacing:1px;margin-left:28px;font-style:normal}
'''

css = css.replace("@font-face{font-family:JetBrains;src:url('assets/fonts/jetbrains-mono-latin-var.woff2') format('woff2');font-weight:100 900}", "")
css += ".band span{z-index:2;background:#172d42aa;padding:2px 0}.cap-note{font-size:19px;font-weight:700;letter-spacing:.4px;color:#a7c5d2}"

voice = []
for sid,start,duration in SCENES:
    path = ROOT / 'assets' / 'voice' / f'{sid}.wav'
    if path.exists():
        raw=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(path)],capture_output=True,text=True)
        actual=float(raw.stdout.strip() or 0)
        voice.append(f'<audio id="voice-{sid}" data-start="{start+0.3}" data-duration="{actual:.3f}" data-track-index="10" data-volume="1" data-audio-group="voiceover" src="assets/voice/{sid}.wav"></audio>')

clips='\n'.join(f'<section id="frame-{sid}" class="clip" data-start="{start}" data-duration="{dur}"><div class="scene" id="s{sid}">{sc[sid]}</div></section>' for sid,start,dur in SCENES)
script='''<script>
window.__timelines=window.__timelines||{};
const tl=gsap.timeline({paused:true});
const slots=[["01",0,9],["02",9,14],["03",23,11],["04",34,12],["05",46,12],["06",58,14],["07",72,12],["08",84,12],["09",96,8],["10",104,8]];
for(const [id,start,duration] of slots){
 const sel="#s"+id+" .appear";
 tl.fromTo(sel,{opacity:0,y:24},{opacity:1,y:0,duration:.8,stagger:.15,ease:"power2.out"},start+.35);
}
tl.fromTo("#ap1",{x:0},{x:650,duration:4,ease:"none"},2);
tl.fromTo("#burst1",{opacity:0,scaleY:.4},{opacity:1,scaleY:1,duration:.12,ease:"power1.out"},3.35);
tl.to("#burst1",{opacity:0,duration:.22},3.78);
tl.fromTo("#scanWindow",{x:0},{x:1425,duration:9.8,ease:"none"},24);
for(const [id,time] of [["pulse1",25.3],["pulse2",28.2],["pulse3",30.9]]){
 tl.fromTo("#"+id,{opacity:0,scaleY:.25},{opacity:1,scaleY:1,duration:.12},time);
 tl.to("#"+id,{opacity:0,duration:.22},time+.23);
}
tl.fromTo("#s08 .bar",{scaleX:0},{scaleX:1,duration:1.4,stagger:.45,ease:"power2.out"},86.2);
// Keep the technical diagrams active while narration explains them.
tl.fromTo("#s02 .hwicon",{scale:1,opacity:.55},{scale:1.25,opacity:1,duration:.7,yoyo:true,repeat:1,stagger:1.45,ease:"sine.inOut"},11.0);
tl.fromTo("#s02 .hwicon",{scale:1,opacity:.55},{scale:1.25,opacity:1,duration:.7,yoyo:true,repeat:1,stagger:1.45,ease:"sine.inOut"},16.8);
for(let i=0;i<4;i++){
 const node="#s04 .loopbox:nth-of-type("+(i*2+1)+") .glyph";
 tl.fromTo(node,{scale:1,opacity:.6},{scale:1.08,opacity:1,duration:.7,yoyo:true,repeat:1,ease:"power2.inOut"},36.2+i*2.25);
}
tl.fromTo("#s05 .model-graphic",{x:-12},{x:12,duration:1.2,yoyo:true,repeat:7,ease:"sine.inOut"},47.2);
tl.fromTo("#s05 .mini-rank i",{scaleX:.08},{scaleX:1,duration:1.8,stagger:.75,ease:"power2.out"},49.0);
tl.fromTo("#s06 .mechanic",{opacity:.5,scale:.95},{opacity:1,scale:1.05,duration:1.0,yoyo:true,repeat:1,stagger:2.4,ease:"sine.inOut"},60.1);
tl.fromTo("#s07 .merge-line",{x:-24,opacity:.4},{x:24,opacity:1,duration:1.2,yoyo:true,repeat:6,ease:"sine.inOut"},74.0);
tl.fromTo("#s08 .lift",{scale:1},{scale:1.04,duration:.8,yoyo:true,repeat:3,ease:"sine.inOut"},89.0);
tl.fromTo("#s09 .covertrack div",{scaleX:0,transformOrigin:"left center"},{scaleX:1,duration:1.3,stagger:.3,ease:"power2.out"},98.1);
tl.fromTo("#s10 .mark",{scale:.97},{scale:1.02,duration:2.2,yoyo:true,repeat:1,ease:"sine.inOut"},106.0);
window.__timelines["main"]=tl;
</script>'''

bed='<audio id="score" src="assets/audio/score.wav" data-start="0" data-duration="112" data-track-index="2" data-volume="0.65"></audio>' if (ROOT/'assets'/'audio'/'score.wav').exists() else ''
html=f'''<!doctype html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=1920,height=1080"><title>Smart Scan — The Solution</title><script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script><style>{css}</style></head><body><main id="root" data-composition-id="main" data-width="1920" data-height="1080" data-duration="112">{clips}{''.join(voice)}{bed}</main>{script}</body></html>'''
(ROOT/'index.html').write_text(html,encoding='utf-8')
print('wrote',ROOT/'index.html','voice clips',len(voice))
