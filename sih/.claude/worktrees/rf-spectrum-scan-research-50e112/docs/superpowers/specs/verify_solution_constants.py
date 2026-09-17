import math

def Q(x):
    return 0.5*math.erfc(x/math.sqrt(2))

def Qinv(p):
    lo,hi=-10.0,10.0
    for _ in range(200):
        mid=(lo+hi)/2
        if Q(mid)>p: lo=mid
        else: hi=mid
    return (lo+hi)/2

Pfa=1e-3
qi=Qinv(Pfa)
print(f"Qinv(1e-3) = {qi:.4f}")

DELTA=0.010      # slot, s
DEAD=0.005       # retune dead time, s
NS_PER_SLOT=100  # independent integration samples per slot

def Pd(m, g):
    Ns=NS_PER_SLOT*m
    return Q((qi - g*math.sqrt(Ns/2.0))/(1.0+g))

print("\nPd(m, gamma) and value-rate Pd/(m*DELTA+DEAD)  [Pfa=1e-3]")
print(f"{'gamma':>7} | " + " | ".join(f"m={m:<2} Pd    rate" for m in (1,2,4,8)))
best={}
for g in (0.05,0.1,0.2,0.3,0.5,1.0,2.0):
    row=[]
    rates={}
    for m in (1,2,4,8):
        p=Pd(m,g); r=p/(m*DELTA+DEAD)
        rates[m]=r
        row.append(f"     {p:6.4f} {r:7.4f}")
    best[g]=max(rates,key=rates.get)
    print(f"{g:>7} |" + "|".join(row) + f"   -> best m={best[g]}")

print("\nOptimal dwell vs SNR:", {f"{g} ({10*math.log10(g):+.0f} dB)":best[g] for g in best})

# --- deadline derivation ---
print("\n--- Deadline derivation (Section 5) ---")
T_max=20.0                 # 3 rpm
beamwidth_deg=1.5
tau_ill=(beamwidth_deg/360.0)*T_max
mdwell=0.010
T_req=60.0
D=T_req*(tau_ill+mdwell)/T_max
print(f"tau_ill = {tau_ill*1000:.1f} ms")
print(f"D_i     = {D*1000:.1f} ms")
N,K=16,2
cycle=(N/K)*(mdwell+DEAD)
print(f"coverage cycle ({N} bands, K={K}) = {cycle*1000:.0f} ms")
print(f"fraction of time committed to coverage = {cycle/D*100:.1f}%")
print(f"fraction free for threat-driven scheduling = {(1-cycle/D)*100:.1f}%")
# tracker case
D_track=2.0*(tau_ill+mdwell)/T_max
print(f"tracker T_req=2s -> D_i = {D_track*1000:.1f} ms  (cycle {cycle*1000:.0f} ms -> {cycle/D_track*100:.0f}% committed)")

# --- fast hopper ---
print("\n--- Fast hopper (Section 8.2) ---")
for hops_per_s,F in ((2000,16),(2000,32),(200,16),(50,16),(20,16)):
    T_hop=1.0/hops_per_s
    n=mdwell/T_hop
    p=1-(1-1/F)**n
    print(f"{hops_per_s:>5} hops/s, |F|={F:<3} -> {n:6.1f} hops/dwell, P(see it | right band) = {p:.3f}")

# --- three-gap / golden ratio dither check ---
print("\n--- Golden-ratio dither: gap structure (three-gap theorem) ---")
g=(math.sqrt(5)-1)/2
for n in (5,10,20,50):
    pts=sorted(((k*g)%1.0) for k in range(1,n+1))
    gaps=[round(pts[(i+1)%n]-pts[i] + (1.0 if i==n-1 else 0.0), 9) for i in range(n)]
    print(f"n={n:<3} distinct gap lengths = {len(set(gaps))}  min gap = {min(gaps):.4f}  (uniform would be {1/n:.4f})")
