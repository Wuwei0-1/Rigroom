"""The Ring of Gyges IV, staged outside the courtyard: Sequence One (the lounge at dawn, the Piraeus, the arrival at
Cephalus's house) and the lounge at the end of Sequence Seven. Same Stage calls as staging4.py; stations name their set.
"""
import math

THRACIANS = ['Thracian %d' % k for k in range(1, 7)]
PIRAEUS_PEOPLE = THRACIANS + ['Fish Seller', 'Child', 'Archer 1', 'Archer 2', 'Servant Boy', 'Niceratus']
HOUSE = ['Cephalus', 'Lysias', 'Euthydemus', 'Thrasymachus', 'Cleitophon', 'Charmantides']
ARRIVE = ['Socrates', 'Glaucon', 'Polemarchus', 'Adeimantus']


def L(spot, face):
    return ('stand', spot, face, 'lounge')


def P(spot, face):
    return ('stand', spot, face, 'piraeus')


def opening(S):
    import courtyard
    # ---------------------------------------------------------------- the lounge, at dawn
    S.scene(0.0, 'lounge', 'INDOOR')
    S.place('Julian', 0.0, ('seat', 'julian', 'lounge'))
    S.place('Aria', 0.0, ('away',))      # the opening starts after Aria and Cleon have gone
    S.place('Cleon', 0.0, ('away',))
    for w in PIRAEUS_PEOPLE + HOUSE + ARRIVE:
        S.place(w, 0.0, ('away',))
    S.prop('ring_on', 0.0, who='Julian', on=False)
    t = S.t('Julian picks up the ring')
    if t is not None:
        e = S.end('Julian picks up the ring')
        S.cam(0.0, 'table')
        S.look('Julian', 0.0, 'ring', t + 1.6)
        S.expr('Julian', 0.0, t + 1.0, 'worry', 0.5)
        S.gesture('point', 'Julian', t + 0.1, t + 1.9, target='ring')
        S.prop('ring_table', t + 1.2)
        S.prop('ring_on', t + 1.25, who='Julian', on=True)
        ts = S.t('Julian picks up the ring', word='He slips')
        S.cam(ts, 'close Julian')
        S.gesture('look_hand', 'Julian', ts, ts + 2.6)
        S.gesture('ring', 'Julian', ts + 2.8, e + 0.6)
        S.expr('Julian', t, e + 1.0, 'curious', 0.7)
    t = S.t('The smell of smog and botanical vapor')
    if t is not None:
        e = S.end('The smell of smog and botanical vapor')
        S.cam(t, 'julian')
        S.expr('Julian', t, e, 'alarm', 0.8)
        S.vanish('Julian', S.t('The smell of smog', word='The air around'), e - 0.1)
        S.cam(S.t('The smell of smog', word='A rush of wind'), 'wide')
    # ---------------------------------------------------------------- the Piraeus, the festival of Bendis
    tp = S.t('The Piraeus, harbour of Athens')
    if tp is None:
        return
    t0 = tp - 0.6
    S.scene(t0, 'piraeus', 'DAY')
    S.place('Julian', t0, P('julian_mid', 0))
    S.prop('hide', t0, who='Julian', on=True)      # unseen in Athens until he turns the ring outward at dawn
    for w in ('Aria', 'Cleon'):
        S.place(w, t0, ('away',))
    # the procession comes up from the harbour along the far side of the street
    tproc = S.t('Blinding sun on white stone')
    if tproc is None:
        tproc = t0
    gap = 1.5
    for k, w in enumerate(THRACIANS):
        x0 = -9.5 - k * gap - (1.2 if k >= 3 else 0)
        S.place(w, t0, P((x0, 1.05), 90))
        S.place(w, tproc + 0.5, P((x0 + 23.0, 1.05), 90), 'move')
        S.place(w, tproc + 0.5 + 23.0 / max(0.5, getattr(S, 'speed_hint', 1.1)) + 1.0, ('away',))
    S.prop('goddess', tproc + 0.5, frm=(-9.5 - 2.5 * gap - 0.6, 1.05), to=(-9.5 - 2.5 * gap - 0.6 + 23.0, 1.05))
    S.cam(tp, 'harbour')
    S.cam(tproc, 'wide')
    # the people of the street
    S.place('Fish Seller', t0, P('fish', 0))
    S.place('Child', t0, P('child', 20))
    S.place('Archer 1', t0, P('archer_a', 200))
    S.place('Archer 2', t0, P('archer_b', 210))
    t = S.t('Julian stands in the middle of it')
    if t is not None:
        e = S.end('Julian stands in the middle of it')
        S.cam(t, 'julian')
        S.look('Julian', t, 'goddess', t + 3.0)
        S.expr('Julian', t, e, 'alarm', 0.6)
        tf = S.t('Julian stands in the middle', word='A fish-seller')
        S.look('Fish Seller', tf, 'Julian')
        S.expr('Fish Seller', tf, tf + 8, 'puzzled', 1.0)
        S.cam(tf, 'close Fish Seller')
        tc = S.t('Julian stands in the middle', word='A child')
        S.gesture('point', 'Child', tc, tc + 3.0, target='shoes')
        S.look('Child', tc, 'shoes', tc + 3.0)
        S.cam(tc, 'close Child')
        ta = S.t('Julian stands in the middle', word='Two Scythian')
        S.place('Archer 1', ta, P('archer_a', 'Julian'), 'move')
        S.place('Archer 2', ta + 0.2, P('archer_b', 'Julian'), 'move')
        S.look('Archer 1', ta + 0.3, 'Julian')
        S.look('Archer 2', ta + 0.5, 'Julian')
        S.expr('Archer 1', ta, ta + 10, 'sullen', 0.8)
        S.cam(ta, 'square')
    t = S.t('I went down yesterday to the Piraeus')
    if t is not None:
        S.cam(t, 'harbour')
        S.place('Archer 1', t + 0.5, P((0.6, 0.0), 'Julian'), 'move')
        S.place('Archer 2', t + 0.9, P((1.4, -0.4), 'Julian'), 'move')
        S.look('Julian', t + 1.0, 'Archer 1')
        S.cam(t + 6.0, 'julian')
    t = S.t('Julian backs into a narrow alley')
    if t is not None:
        e = S.end('Julian backs into a narrow alley')
        S.place('Julian', t, P('alley_in', 'Archer 1'), 'move')
        S.cam(t, 'alley')
        tr = S.t('Julian backs into', word='His fingers')
        S.gesture('ring', 'Julian', tr, tr + 2.4)
        S.visible('Julian', S.t('Julian backs into', word='the bezel slides'), False, 0.8)
        ta = S.t('Julian backs into', word='The archers')
        S.place('Archer 1', ta, P('archer_corner_a', 'alley'), 'move')
        S.place('Archer 2', ta + 0.3, P('archer_corner_b', 'alley'), 'move')
        S.look('Archer 1', ta + 1.5, 'alley', e - 1.0)
        S.look('Archer 2', ta + 1.8, 'alley', e - 1.0)
        S.place('Archer 1', e - 0.8, P('archer_on_a', 270), 'move')
        S.place('Archer 2', e - 0.5, P('archer_on_b', 270), 'move')
        S.place('Archer 1', e + 12.0, ('away',))
        S.place('Archer 2', e + 12.0, ('away',))
    t = S.t('Julian raises his hand in front of his face')
    if t is not None:
        e = S.end('Julian raises his hand in front of his face')
        S.cam(t, 'close Julian')
        S.gesture('look_hand', 'Julian', t + 0.2, e + 0.4)
        S.visible('Julian', S.t('Julian raises his hand', word='the hand flickers'), True, 0.4)
        S.visible('Julian', S.t('Julian raises his hand', word='Inward'), False, 0.4)
        S.expr('Julian', t, e + 3, 'alarm', 0.7)
    t = S.t('The Ring of Gyges. We spent two years')
    if t is not None:
        S.expr('Julian', t, S.end('The Ring of Gyges. We spent two years'), 'wonder', 0.8)
    t = S.t('Across the square, beside a tall young man')
    if t is not None:
        e = S.end('Across the square, beside a tall young man')
        S.place('Socrates', t - 0.5, P('square_a', 250))
        S.place('Glaucon', t - 0.5, P((9.0, -2.2), 250))
        S.place('Socrates', t + 0.3, P('soc_stop', 'alley'), 'move')
        S.place('Glaucon', t + 0.5, P('glaucon_stop', 'Socrates'), 'move')
        S.cam(t, 'square')

    t = S.t('Socrates halts mid-stride')
    if t is not None:
        S.look('Socrates', t + 0.2, 'alley', t + 3.6)
        S.expr('Socrates', t + 0.2, t + 4.0, 'puzzled', 1.0)
        S.cam(t, 'close Socrates')
        tb = S.t('Socrates halts mid-stride', word='Before he')
        S.place('Servant Boy', t, P('boy_run', 180))
        S.place('Servant Boy', tb, P('boy_at', 'Socrates'), 'move')
        S.cam(tb, 'group')
    t = S.t('Polemarchus desires you to wait')
    if t is not None:
        S.look('Socrates', t, 'Servant Boy', t + 2.5)
    t = S.t('pushes through the crowd')
    if t is not None:
        for k, (w, spot) in enumerate((('Polemarchus', 'pol_at'), ('Adeimantus', 'adei_at'), ('Niceratus', 'nic_at'))):
            S.place(w, t - 0.6, P((10.5 + k * 0.8, -0.3 + 0.5 * (k % 2)), 250))
            S.place(w, t + 0.2 + 0.4 * k, P(spot, 'Socrates'), 'move')
        S.cam(t, 'group')
    t = S.t('I perceive, Socrates, that you and your companion')
    if t is not None:
        S.gesture('spread', 'Polemarchus', t + 3.0, t + 7.0)
    t = S.t('With horses! That is a novelty')
    if t is not None:
        S.expr('Socrates', t, S.end('With horses!'), 'smile', 0.8)
    t = S.t('The group sets off up the hill')
    if t is not None:
        e = S.end('The group sets off up the hill')
        for k, w in enumerate(('Polemarchus', 'Niceratus', 'Adeimantus', 'Servant Boy', 'Glaucon')):
            S.place(w, t + 0.2 + 0.35 * k, P(('hill_a', 'hill_b', 'hill_c')[k % 3] if k < 3 else 'hill_a', 270), 'move')
        S.look('Socrates', t + 1.0, 'alley', t + 3.0)
        S.place('Socrates', t + 3.2, P('hill_a', 270), 'move')
        S.place('Julian', t + 4.4, P('pol_at', 270), 'move')
        S.cam(t, 'hill')
        S.cam(S.t('The group sets off', word='Socrates glances'), 'close Socrates')
        S.cam(S.t('The group sets off', word='Julian, unseen'), 'hill')
    # ---------------------------------------------------------------- Cephalus's courtyard, late afternoon
    tc = S.t('A courtyard open to the sky')
    if tc is None:
        return
    t1 = tc - 0.6
    S.scene(t1, 'court', 'LATE AFTERNOON')
    for w in PIRAEUS_PEOPLE:
        S.place(w, t1, ('away',))
    S.place('Cephalus', t1, ('seat', 'cephalus'))
    S.place('Euthydemus', t1, ('seat', 'arc135'))
    S.place('Lysias', t1, ('seat', 'arc158'))
    S.place('Charmantides', t1, ('seat', 'arc178'))
    S.place('Cleitophon', t1, ('seat', 'bench2'))
    S.place('Thrasymachus', t1, ('seat', 'bench1'))
    S.cam(tc, 'altar')
    te = S.t('In a cushioned chair sits CEPHALUS')
    if te is not None:
        S.cam(te, 'close Cephalus')
        S.cam(S.t('In a cushioned chair', word='apart from them'), 'close Thrasymachus')
        S.expr('Thrasymachus', te, te + 14, 'smug', 0.7)
    # the visitors come in at the gate and sit; Julian slips in behind them
    ti = S.t('Julian slips in behind the last')
    tin = (ti - 8.5) if ti is not None else (te if te is not None else tc)
    for k, (w, seat) in enumerate((('Polemarchus', 'arc110'), ('Socrates', 'arc70'), ('Glaucon', 'arc45'), ('Adeimantus', 'arc25'))):
        x0 = 5.3 + 0.8 * k
        ta = tin + 0.3 + 1.6 * k
        S.place(w, t1, ('stand', (x0, -2.35), 270))
        S.place(w, ta, ('stand', (3.7, -2.3), 'mid'), 'move')
        S.place(w, ta + (x0 - 3.7) / 0.85 + 1.4, ('seat', seat), 'move')
    S.place('Julian', t1, ('stand', (9.0, -2.35), 270))
    S.visible('Julian', t1, False, 0.1)
    if ti is not None:
        S.cam(ti - 6.0, 'gate')
        S.place('Julian', ti + 0.2, ('stand', (4.1, -2.3), 'mid'), 'move')
        S.place('Julian', ti + 0.2 + 4.9 / 0.85 + 1.0, ('stand', 'column', 'mid'), 'move')
        S.cam(ti + 1.5, 'wide')
    t = S.t('Cephalus laughs, a dry, warm sound')
    if t is not None:
        S.expr('Cephalus', t, t + 3.0, 'laugh', 1.0)
        S.cam(t, 'close Cephalus')
    t = S.t('He goes out laughing to the altar')
    if t is not None:
        e = S.end('He goes out laughing to the altar')
        S.expr('Cephalus', t, e + 2, 'laugh', 0.8)
        S.place('Cephalus', t + 0.2, ('stand', 'altar', 270), 'move')
        S.place('Polemarchus', t + 2.6, ('seat', 'cephalus'), 'move')
        S.cam(t, 'follow Cephalus')
        S.cam(S.t('He goes out laughing', word='Polemarchus takes'), 'chair')
        S.place('Cephalus', e + 9.0, ('away',))
    t = S.t('Against his column, Julian goes very still')
    if t is not None:
        S.expr('Julian', t, S.end('That was us. That was the whole Mirror Force', 1.0), 'alarm', 0.8)
        S.cam(t, 'column_view')
    t = S.t('Julian looks down at the empty space')
    if t is not None:
        S.gesture('look_hand', 'Julian', t + 0.2, S.end('Julian looks down at the empty space', 0.6))
        S.cam(t, 'close Julian')
    t = S.t('On his couch, THRASYMACHUS has been trying')
    if t is not None:
        S.cam(t, 'close Thrasymachus')
        S.place('Thrasymachus', S.t('On his couch', word='Now he gathers'), ('stand', 'mid', 'Socrates'), 'move')
        S.expr('Thrasymachus', t, S.end('On his couch, THRASYMACHUS', 2.0), 'sullen', 1.0)


def ending(S, t0):
    """The lounge again: Julian in his seat, Aria back for her slate, the blinds up and his shadow on the floor."""
    S.place('Julian', t0 - 0.2, ('seat', 'julian', 'lounge'))
    S.prop('appear', t0 - 0.1, who='Julian', dur=1.2, shadow=True)
    S.visible('Julian', t0 - 0.15, True, 0.05)
    S.place('Aria', 0.0, ('away',))
    S.cam(t0, 'wide')
    t = S.t('The door opens. ARIA steps back in')
    if t is not None:
        S.prop('door', t + 0.2, open=True, dur=1.0)
        S.place('Aria', t + 0.3, L('door_in', 90))
        S.place('Aria', t + 0.6, L('front_left', 'Julian'), 'move')
        S.prop('door', t + 4.0, open=False, dur=1.2)
        S.cam(t, 'door')
        S.cam(S.t('The door opens', word='and stops'), 'close Aria')
    t = S.t("You haven't moved")
    if t is not None:
        S.expr('Aria', t, t + 3, 'puzzled', 0.8)
    t = S.t('Julian looks down at his hand')
    if t is not None:
        S.gesture('look_hand', 'Julian', t + 0.1, S.end('Julian looks down at his hand', 0.8))
        S.cam(t, 'close Julian')
    t = S.t('I went to a party in the Piraeus')
    if t is not None:
        S.expr('Julian', t, t + 4, 'smile', 0.5)
    t = S.t('In ten minutes?')
    if t is not None:
        S.expr('Aria', t, t + 3, 'puzzled', 1.0)
    t = S.t('He stands, crosses to the window and pulls up the blinds')
    if t is not None:
        e = S.end('He stands, crosses to the window')
        S.place('Julian', t + 0.2, L('window', 90), 'move')
        S.cam(t, 'window')
        tb = S.t('He stands, crosses to the window', word='Sunlight floods')
        S.prop('blinds', tb - 1.0, dur=1.8)
        S.gesture('point_up', 'Julian', tb - 1.3, tb + 0.6)
        S.look('Aria', t + 0.5, 'Julian')
        S.cam(S.t('He stands, crosses', word='For the first time'), 'window')
    t = S.t("Call Cleon. We're going back down")
    if t is not None:
        S.place('Julian', t - 0.6, L('window', 'Aria'), 'move')
        S.expr('Julian', t, t + 4, 'determined', 0.8)
        S.cam(t, 'close Julian')
