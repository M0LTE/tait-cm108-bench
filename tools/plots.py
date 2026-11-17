import json, glob, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
S = '/tmp/claude-1000/-home-tf-src/9ec190c6-ad06-4b46-85ae-5eed52b0e8af/scratchpad/e2e/'; OUT = '/home/tf/src/tait-cm108-bench/img/'
THEMES = {'light': dict(bg='#fcfcfb', ink='#0b0b0b', ink2='#52514e', grid='#e4e3df', s=['#2a78d6', '#eb6834']),
          'dark': dict(bg='#1a1a19', ink='#f0efec', ink2='#c3c2b7', grid='#383835', s=['#3987e5', '#d95926'])}
def sweeps(w):
    rs = [json.load(open(f)) for f in sorted(glob.glob(f'{S}e2e-{w}-*-sweep*.json'))]
    f = np.array([r['f'] for r in rs[0]['rows']], float)
    get = lambda k: np.nanmean([[np.nan if r[k] is None else r[k] for r in x['rows']] for x in rs], 0)
    return f, get('rel_db'), get('h2_dbc'), get('h3_dbc'), get('noise_dbfs_hz')
def mtone(w):
    rs = [json.load(open(f))['rows'] for f in sorted(glob.glob(f'{S}e2e-{w}-*-mtone.json'))]
    f = np.array([r['f'] for r in rs[0]]); gd = np.mean([[r['gd_us'] for r in x] for x in rs], 0)
    gds = np.array([np.mean(gd[max(0,i-(1 if f[i]<1000 else 4)):i+(2 if f[i]<1000 else 5)]) for i in range(len(gd))]); return f, gds
def sinad(w):
    rs = [json.load(open(f))['rows'] for f in sorted(glob.glob(f'{S}e2e-{w}-*-sinad*.json'))]
    p = np.array([r['pct'] for r in rs[0]]); return p, np.mean([[r['sinad_db'] for r in x] for x in rs], 0)
# Wide SINAD against deviation, 1 kHz, measured 15 November at the same -80 dBm (deviation-referenced, so the board change does not affect it)
wide_pct = np.array([0.31, 0.61, 0.97, 1.53, 2.16, 3.06])/5*100; wide_sinad = np.array([28, 34, 37.5, 40, 39.5, 37.5])

def style(ax, t):
    ax.set_facecolor(t['bg']); ax.figure.set_facecolor(t['bg'])
    for sp in ('top', 'right'): ax.spines[sp].set_visible(False)
    for sp in ('left', 'bottom'): ax.spines[sp].set_color(t['grid'])
    ax.tick_params(colors=t['ink2'], labelsize=9, length=0); ax.grid(True, color=t['grid'], lw=0.8); ax.set_axisbelow(True)
    ax.xaxis.label.set_color(t['ink2']); ax.yaxis.label.set_color(t['ink2'])
def finish(fig, ax, t, title, sub, name, mode):
    fig.text(0.07, 0.95, title, color=t['ink'], fontsize=12, weight='bold', ha='left', va='top')
    fig.text(0.07, 0.89, sub, color=t['ink2'], fontsize=9, ha='left', va='top')
    leg = ax.legend(frameon=False, fontsize=9, loc=LEG.get(name, 'lower left'), labelcolor=t['ink'])
    fig.subplots_adjust(left=0.1, right=0.97, top=0.82, bottom=0.14)
    fig.savefig(f'{OUT}{name}-{mode}.png', dpi=200); plt.close(fig)
LEG = {'sinad': 'upper right', 'group-delay': 'upper right', 'distortion': 'upper left', 'noise': 'upper right'}
hz = matplotlib.ticker.FuncFormatter(lambda v, _: f'{v/1000:g} kHz' if v >= 1000 else f'{v:g} Hz')
for mode, t in THEMES.items():
    W = sweeps('wide'); N = sweeps('narrow')
    # 1 amplitude
    fig, ax = plt.subplots(figsize=(7.5, 4.2)); style(ax, t)
    for (f, L, *_), lbl, c in ((W, 'Wide (25 kHz)', t['s'][0]), (N, 'Narrow (12.5 kHz)', t['s'][1])):
        ax.plot(f, np.maximum(L, -61), color=c, lw=2, label=lbl)
    ax.set_xscale('log'); ax.set_xlim(10, 12000); ax.set_ylim(-40, 3); ax.xaxis.set_major_formatter(hz)
    ax.axhline(-3, color=t['ink2'], lw=0.8, ls=(0, (3, 3))); ax.text(300, -2.4, '-3 dB', color=t['ink2'], fontsize=8, ha='center')
    ax.text(6900, -2.0, '6.3 kHz', color=t['s'][0], fontsize=8, ha='left'); ax.text(3500, -5.5, '3.9 kHz', color=t['s'][1], fontsize=8, ha='right')
    ax.set_ylabel('dB relative to 1 kHz')
    finish(fig, ax, t, 'End-to-end amplitude response', 'Sound card to sound card through both radios, T12 to R2, mean of 6 sweeps per width', 'response', mode)
    # 2 group delay
    fig, ax = plt.subplots(figsize=(7.5, 4.2)); style(ax, t)
    for w, lbl, c, top in (('wide', 'Wide', t['s'][0], 8000), ('narrow', 'Narrow', t['s'][1], 5000)):
        f, g = mtone(w); m = (f >= 40) & (f <= top); ax.plot(f[m], g[m], color=c, lw=2, label=lbl)
    ax.set_xscale('log'); ax.set_xlim(40, 9000); ax.set_ylim(-100, 1000); ax.xaxis.set_major_formatter(hz)
    ax.set_ylabel('microseconds, relative to 211 Hz to 3 kHz')
    finish(fig, ax, t, 'Group delay', 'Flat across the passband on both widths; the low-frequency coupling adds delay below about 300 Hz', 'group-delay', mode)
    # 3 distortion
    fig, ax = plt.subplots(figsize=(7.5, 4.2)); style(ax, t)
    for (f, L, h2, h3, _), lbl, c, top in ((W, 'Wide', t['s'][0], 4000), (N, 'Narrow', t['s'][1], 3000)):
        thd = 10*np.log10(10**(h2/10) + 10**(np.nan_to_num(h3, nan=-120)/10)); m = (f >= 50) & (f <= top)
        ax.plot(f[m], thd[m], color=c, lw=2, label=lbl)
    ax.set_xscale('log'); ax.set_xlim(50, 4000); ax.set_ylim(-65, -25); ax.xaxis.set_major_formatter(hz)
    ax.set_ylabel('2nd + 3rd harmonic, dBc')
    finish(fig, ax, t, 'Distortion against modulating frequency', 'Tone at 28% of the channel maximum; rises about 6 dB per octave above 1 kHz (receiver)', 'distortion', mode)
    # 4 SINAD
    fig, ax = plt.subplots(figsize=(7.5, 4.2)); style(ax, t)
    for w, lbl, c in (('wide', 'Wide', t['s'][0]), ('narrow', 'Narrow', t['s'][1])):
        p, sn = sinad(w); ax.plot(p, sn, color=c, lw=2, marker='o', ms=6, label=lbl)
    ax.axvline(60, color=t['ink2'], lw=0.8, ls=(0, (3, 3))); ax.text(61, 21.5, '60%: standard test point', color=t['ink2'], fontsize=8)
    ax.set_xlim(0, 95); ax.set_ylim(18, 42); ax.set_xlabel('1 kHz tone deviation, % of the channel maximum'); ax.set_ylabel('SINAD, 300 Hz to 3 kHz, dB')
    finish(fig, ax, t, 'SINAD against deviation at -80 dBm', 'Mean of four runs per width; rises to a peak at 30 to 40% of the maximum, then receive distortion takes over', 'sinad', mode)
    # 5 noise floor
    fig, ax = plt.subplots(figsize=(7.5, 4.2)); style(ax, t)
    for (f, L, h2, h3, n), lbl, c in ((W, 'Wide', t['s'][0]), (N, 'Narrow', t['s'][1])):
        m = (f >= 20) & (f <= 8000); ax.plot(f[m], n[m], color=c, lw=2, label=lbl)
    ax.set_xscale('log'); ax.set_xlim(20, 8000); ax.set_ylim(-118, -90); ax.xaxis.set_major_formatter(hz)
    ax.set_ylabel('dBFS/Hz at the receiving sound card')
    finish(fig, ax, t, 'Receive noise under an unmodulated carrier', '-80 dBm, CM108B input at -12 dB, averaged over 15% bands around each sweep frequency', 'noise', mode)
print('done')
