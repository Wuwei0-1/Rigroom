"""The Ring of Gyges IV, staged: for each sequence, who is where and what the stage directions make them do.

stage(seq, S, i0, i1) fills S (athens.Stage) from the script's own words: S.t('a phrase') is the time that element
starts, so the staging follows the voices however long they turn out. A phrase missing from the stretch being built
(a test range) gives None, and whatever is timed by it is skipped.

Stations: ('seat', seat), ('stand', spot or (x, y), face), ('floor', spot, face), ('away',); a set name may follow
(default the courtyard). Seats and spots are in courtyard.py.
"""
import math

import courtyard

# where everyone sits once Cephalus has gone to his sacrifice and Polemarchus has taken his father's chair
COMPANY = {
    'Polemarchus': ('seat', 'cephalus'), 'Socrates': ('seat', 'arc70'), 'Glaucon': ('seat', 'arc45'), 'Adeimantus': ('seat', 'arc25'),
    'Euthydemus': ('seat', 'arc135'), 'Lysias': ('seat', 'arc158'), 'Charmantides': ('seat', 'arc178'), 'Cleitophon': ('seat', 'bench2'),
    'Thrasymachus': ('seat', 'bench1'),
}
# later that night, Adeimantus has moved up beside Polemarchus (to the chair Polemarchus left); Euthydemus has dozed off
LATER = dict(COMPANY, Adeimantus=('seat', 'arc110'))
# before dawn: Cephalus's chair stands empty; Charmantides has gone home
DAWN = dict(COMPANY, Polemarchus=('seat', 'arc110'))
DAWN.pop('Charmantides')


def front_of(seat, d=0.55):
    x, y, yaw = courtyard.SEATS[seat]
    a = math.radians(yaw)
    return (x + math.sin(a) * d, y - math.cos(a) * d)


def seat_all(S, t, places, extra=None):
    for who, st in dict(places, **(extra or {})).items():
        S.place(who, t, st)


def all_seated(places):
    return [w for w, st in places.items() if st[0] == 'seat']


def seq2(S):
    S.prop('hide', 0.0, who='Julian', on=True)
    S.scene(0.0, 'court', 'LATE AFTERNOON')
    seat_all(S, 0.0, COMPANY, {'Thrasymachus': ('stand', 'mid', 'Socrates'), 'Julian': ('stand', 'column', 'mid')})
    S.visible('Julian', 0.0, False)
    t = S.t('The young men shrink back')
    if t is not None:
        it = S.it('The young men shrink back')
        for w in all_seated(COMPANY):
            if w != 'Thrasymachus':
                S.lean(w, t + 0.4, t + 22.0, -7.0)
                S.expr(w, t + 0.4, t + 20.0, 'worry', 0.8)
        tj = it['t'] + it['secs'] * 0.72
        S.lean('Julian', tj, tj + 3.0, -11.0)
        S.expr('Julian', tj - 0.1, tj + 4.0, 'alarm', 1.0)
    t, e = S.t('What folly, Socrates'), S.end('What folly, Socrates')
    if t is not None:
        S.gesture('point', 'Thrasymachus', t + 0.3, t + 3.6, target='Socrates')
        S.gesture('spread', 'Thrasymachus', e - 7.5, e - 3.2)
        S.lean('Thrasymachus', t, t + 4.0, 9.0)
    e = S.end('why do you not praise me')
    if e is not None:
        S.gesture('spread', 'Thrasymachus', e - 3.8, e + 0.4)
        S.expr('Thrasymachus', e - 3.8, e + 0.8, 'smug', 1.0)
    t = S.t("don't be hard upon us")
    if t is not None:
        S.expr('Socrates', t, S.end("don't be hard upon us"), 'worry', 0.6)
    t = S.t("Thrasymachus's face darkens")
    if t is not None:
        S.expr('Thrasymachus', t, S.end('have you got a nurse', 0.5) or t + 6, 'clench', 1.0)
        S.cam(t, 'close Thrasymachus')
    # he paces, gathering force, and comes back to the middle
    t = S.t('He paces the courtyard')
    if t is not None:
        S.place('Thrasymachus', t + 0.3, ('stand', 'pace_b', 'Socrates'), 'move')
        S.place('Thrasymachus', S.t('Consider further, most foolish', 0.45), ('stand', 'pace_a', 'Socrates'), 'move')
        S.place('Thrasymachus', S.t('But look at the highest form', 0.25), ('stand', 'mid', 'Socrates'), 'move')
        S.cam(t + 0.2, 'follow Thrasymachus')
    # he makes for the gate; Glaucon and Adeimantus rise and block his way; he sits again, sullen
    t = S.t('Thrasymachus gathers his cloak to leave')
    if t is not None:
        S.place('Thrasymachus', t + 0.6, ('stand', 'toward_gate', 'gate'), 'move')
        S.place('Adeimantus', t + 1.2, ('stand', 'block_a', 'Thrasymachus'), 'move')
        S.place('Glaucon', t + 1.6, ('stand', 'block_b', 'Thrasymachus'), 'move')
        S.cam(t + 0.4, 'wide')
        S.expr('Thrasymachus', t, t + 9, 'frown', 1.0)
    t = S.t('Thrasymachus sits again')
    if t is not None:
        S.place('Thrasymachus', t, ('seat', 'bench1'), 'move')
        S.place('Glaucon', t + 0.8, ('seat', 'arc45'), 'move')
        S.place('Adeimantus', t + 0.4, ('seat', 'arc25'), 'move')
        S.expr('Thrasymachus', t, S.t('Let this, Socrates') or t + 30, 'sullen', 1.0)
        S.cam(t, 'follow Thrasymachus')
    t = S.t('The heat of the day still hangs')
    if t is not None:
        S.redden('Thrasymachus', t + 1.0, (S.end('Let this, Socrates') or t + 12) + 1.0)
        S.cam(S.t('The heat of the day still hangs', word='Sweat'), 'close Thrasymachus')
        S.expr('Thrasymachus', t, S.end('Let this, Socrates') or t + 10, 'sullen', 1.0)
        S.expr('Socrates', S.t('The heat of the day', word='For a moment'), S.end('The heat of the day'), 'curious', 1.0)
    t = S.t('And the result of the whole discussion')
    if t is not None:
        S.gesture('spread', 'Socrates', t - 0.2, S.end('And the result of the whole discussion', 0.3))
    t = S.t('He sits back, as if the evening is over')
    if t is not None:
        S.lean('Socrates', t, t + 8, -5.0)
        S.place('Glaucon', S.t('He sits back', word='GLAUCON'), ('stand', front_of('arc45'), 'Socrates'), 'move')
        S.cam(S.t('He sits back', word='In the corner'), 'follow Glaucon')


def seq3(S):
    S.prop('hide', 0.0, who='Julian', on=True)
    S.scene(0.0, 'court', 'DUSK')
    seat_all(S, 0.0, COMPANY, {'Glaucon': ('stand', 'mid', 'Socrates'), 'Julian': ('stand', 'column', 'mid')})
    S.visible('Julian', 0.0, False)
    t = S.t('Servants light the oil lamps')
    if t is not None:
        S.lamp(t + 0.5, 'all', True, 1.6)
    t = S.t('~he begins to walk')
    if t is not None:
        S.place('Glaucon', t + 0.2, ('stand', (-0.75, 0.75), 'Socrates'), 'move')
        S.place('Glaucon', t + 6.5, ('stand', (0.3, 0.45), 'Socrates'), 'move')
    t = S.t("Julian's thumb finds the ring")
    if t is not None:
        S.gesture('ring', 'Julian', t + 0.3, S.end("Julian's thumb finds the ring", 2.5))
        S.cam(t, 'close Julian')
    t = S.t("Socrates's eyes drift past him")
    if t is not None:
        e = S.end("Socrates's eyes drift past him")
        S.look('Socrates', t + 1.2, 'Julian', e + 2.5)
        S.cam(t, 'close Socrates')
        S.cam(S.t("Socrates's eyes drift past him", word='to the lamplit'), 'close Julian')
        S.cam(S.t("Socrates's eyes drift past him", word='They rest'), 'close Socrates')
    t = S.t('ADEIMANTUS rises beside his brother')
    if t is not None:
        S.place('Adeimantus', t + 0.2, ('stand', 'mid_right', 'Socrates'), 'move')
        S.place('Glaucon', t + 0.4, ('stand', 'mid_left', 'Socrates'), 'move')
        S.cam(t, 'follow Adeimantus')
    t = S.t('So I say: not only prove')
    if t is not None:
        S.gesture('look_hand', 'Julian', t + 2.0, S.end('The words hang in the lamplight', -0.4))
    t = S.t('The words hang in the lamplight')
    if t is not None:
        S.cam(t, 'close Julian')
    t = S.t('Julian slides down the column')
    if t is not None:
        S.place('Julian', t + 0.4, ('floor', 'column_floor', 'mid'), 'move')
        S.cam(t, 'column_view')
    t = S.t('~delighted')
    if t is not None:
        S.expr('Glaucon', t, t + 6, 'smile', 0.6)
        S.expr('Adeimantus', t, t + 6, 'smile', 0.5)


def seq4(S):
    S.prop('hide', 0.0, who='Julian', on=True)
    S.scene(0.0, 'court', 'NIGHT')
    seat_all(S, 0.0, COMPANY, {'Julian': ('floor', 'column_floor', 'mid')})
    S.visible('Julian', 0.0, False)
    S.lamp(0.0, 'all', True, 0.0)
    t = S.t('horsemen gallop past carrying torches')
    if t is not None:
        tt = S.t('horsemen gallop past', word='Through the open gate')
        S.prop('torches', tt + 0.6, n=5, gap=1.0, dur=3.2)
        S.look('Julian', tt, 'gate', S.end('horsemen gallop past', 1.5))
        S.cam(tt - 0.2, 'gate')
    t = S.t('Laughter around the semicircle')
    if t is not None:
        for w in list(COMPANY) + ['Julian']:
            S.expr(w, t, t + 3.2, 'smile', 0.9)
    t = S.t('Julian glances down at the ring')
    if t is not None:
        S.gesture('look_hand', 'Julian', t, S.end('Brass. Of course', 1.0) or t + 5)
        S.cam(t, 'close Julian')
    t = S.t('He stops, then laughs at himself')
    if t is not None:
        S.expr('Socrates', t, t + 4, 'smile', 1.0)
    t = S.t('Julian turns the ring slowly round')
    if t is not None:
        S.gesture('ring', 'Julian', t, S.end('Julian turns the ring slowly round', 2.0))
        S.cam(t, 'close Julian')
    t = S.t('city of pigs')
    if t is not None:
        S.expr('Glaucon', t, S.end('city of pigs'), 'smug', 0.8)


def seq5(S):
    S.prop('hide', 0.0, who='Julian', on=True)
    S.scene(0.0, 'court', 'LATER THAT NIGHT')
    seat_all(S, 0.0, LATER, {'Julian': ('floor', 'back_column_floor', 'mid')})
    S.visible('Julian', 0.0, False)
    S.lamp(0.0, 'all', True, 0.0)
    S.sleep('Euthydemus', 0.0)
    S.lean('Lysias', 0.0, 1e6, -9.0)
    S.quiet.add('Euthydemus')
    t = S.t('POLEMARCHUS leans across to ADEIMANTUS')
    if t is not None:
        e = S.end('Shall we let him off') or t + 12
        S.lean('Polemarchus', t + 1.0, e + 0.6, 14.0)
        S.look('Polemarchus', t + 1.0, 'Adeimantus', e + 0.3)
        S.look('Adeimantus', t + 1.5, 'Polemarchus', e + 0.3)
        S.cam(S.t('POLEMARCHUS leans across', word='Only Julian'), 'close Julian')
    t = S.t('He rises and stands at the centre')
    if t is not None:
        S.place('Socrates', t + 0.2, ('stand', 'mid', 'Polemarchus'), 'move')
        S.cam(t, 'follow Socrates')
    t = S.t('GLAUCON leans forward, half laughing')
    if t is not None:
        S.lean('Glaucon', t, S.end('pull off their coats') or t + 8, 10.0)
        S.expr('Glaucon', t, S.end('pull off their coats') or t + 8, 'smile', 0.6)
    t = S.t('He points up, past the edge of the roof')
    if t is not None:
        e = S.end('The eyes, when they are turned') or t + 12
        S.gesture('point_up', 'Socrates', t, t + 5.5)
        for w in LATER:
            if w not in ('Socrates', 'Euthydemus'):
                S.look(w, t + 0.6, 'sky', t + 3.5)
    t = S.t('The young men roar with laughter')
    if t is not None:
        e = S.end('The young men roar with laughter')
        for w in LATER:
            if w != 'Euthydemus':
                S.expr(w, t, e + 0.5, 'laugh', 1.0)
                S.nod(w, t, e, 6.0)
        tj = S.t('The young men roar with laughter', word='In the corner')
        S.expr('Julian', tj, e + 0.6, 'laugh', 1.0)
        S.nod('Julian', tj, e + 0.4, 7.0)
        S.cam(tj - 0.2, 'close Julian')
    t = S.t('The laughter dies. Every head turns')
    if t is not None:
        e = S.end('Perhaps the goddess, Polemarchus') or t + 12
        for w in LATER:
            if w not in ('Euthydemus',):
                S.look(w, t + 0.3, 'Julian', S.end('Who was that', 1.5) or t + 6)
        S.half_rise('Polemarchus', S.t('The laughter dies', word='POLEMARCHUS'), S.t('Polemarchus sits again') or t + 8, 0.4)
        S.cam(t, 'wide')
    t = S.t('Julian presses both hands over his mouth')
    if t is not None:
        e = S.end('Perhaps the goddess, Polemarchus') or t + 10
        S.gesture('hands_mouth', 'Julian', t, e + 0.5)
        S.expr('Julian', t, e + 0.5, 'alarm', 1.0)
        S.look('Socrates', S.t('Julian presses both hands', word='Socrates looks'), 'Julian', e + 0.2)
        S.cam(S.t('Julian presses both hands', word='Socrates looks'), 'close Socrates')
    t = S.t('Polemarchus sits again')
    if t is not None:
        S.expr('Polemarchus', t, t + 6, 'puzzled', 1.0)
    t = S.t('The lamps gutter in a sudden draught')
    if t is not None:
        S.lamp(t + 1.0, 'all', False, 0.9)
        S.cam(t, 'high')


def seq6(S):
    S.prop('hide', 0.0, who='Julian', on=True)
    S.scene(0.0, 'court', 'DEEP NIGHT')
    seat_all(S, 0.0, LATER, {'Julian': ('stand', 'wall_front', 'wall')})
    S.visible('Julian', 0.0, False)
    S.sleep('Euthydemus', 0.0)
    S.lean('Lysias', 0.0, 1e6, -9.0)
    S.quiet.add('Euthydemus')
    t = S.t('A servant relights a single lamp')
    if t is not None:
        S.lamp(t + 1.2, courtyard.BACK_LAMP, True, 0.0)
        S.cam(t, 'high')
        S.cam(S.t('A servant relights', word='At once'), 'wall')
    t = S.t('Julian stands among the shadows')
    if t is not None:
        S.cam(t, 'wall_julian')
        S.look('Julian', 0.0, 'wall', S.end('Julian stands among the shadows', 2.0))
    t = S.t('Behold! Human beings')
    if t is not None:
        S.cam(t + 6.0, 'wall')
    t = S.t('Socrates sits calmly in the lamplight')
    if t is not None:
        S.cam(t, 'close Socrates')
    t = S.t('Julian looks at the shadows on the wall')
    if t is not None:
        S.cam(t, 'wall_julian')
        S.look('Julian', t, 'wall', S.end('Must go down', 1.0) or t + 8)


def seq7(S):
    S.prop('hide', 0.0, who='Julian', on=True)
    _tu = S.t('In the corner, Julian stands up')
    if _tu is not None:
        S.prop('hide', _tu - 0.05, who='Julian', on=False)
    S.scene(0.0, 'court', 'BEFORE DAWN')
    seat_all(S, 0.0, DAWN, {'Julian': ('floor', 'corner_floor', 'mid')})
    S.visible('Julian', 0.0, False)
    S.lamp(0.0, courtyard.BACK_LAMP, True, 0.0)
    S.prop('garland', 0.0)
    for w in ('Thrasymachus', 'Polemarchus', 'Euthydemus', 'Lysias', 'Cleitophon'):
        S.sleep(w, 0.0)
        S.quiet.add(w)
    S.cam(S.t('Most of the company is asleep'), 'high')
    # Socrates turns to the corner and speaks the ring of Gyges to it
    t = S.t('Socrates turns in his chair until he faces the column')
    rise = S.t('Socrates rises, steps carefully')
    if t is not None:
        x, y, yaw = courtyard.SEATS['arc70']
        cx, cy = courtyard.SPOTS['corner_floor']
        want = math.degrees(math.atan2(cx - x, -(cy - y)))
        d = ((want - yaw + 180) % 360) - 180
        S.turn('Socrates', t + 0.3, rise if rise is not None else 1e6, max(-55.0, min(55.0, d * 0.75)))
        S.look('Socrates', t + 0.6, 'Julian', rise)
        S.cam(t, 'close Socrates')
    t = S.t('Glaucon follows his gaze to the column')
    if t is not None:
        S.look('Glaucon', t + 0.2, 'corner_up', t + 3.2)
        S.look('Glaucon', t + 3.2, 'Socrates', t + 9)
        S.expr('Glaucon', t + 2.5, t + 8, 'puzzled', 1.0)
        S.cam(t, 'close Glaucon')
    t = S.t('In the corner, Julian stands up')
    if t is not None:
        e = S.end('In the corner, Julian stands up')
        S.place('Julian', t + 0.3, ('stand', 'corner', 'mid'), 'move')
        S.gesture('look_hand', 'Julian', t + 2.2, e - 0.6)
        S.visible('Julian', e - 1.4, True, 1.2)
        S.cam(t, 'corner')
        S.cam(S.t('In the corner, Julian stands up', word='He looks'), 'close Julian')
    t = S.t('a new shadow appears')
    if t is not None:
        S.cam(t, 'wall')
    t = S.t('No one sees it but Socrates')
    if t is not None:
        S.expr('Socrates', t, t + 5, 'smile', 0.55)
        S.cam(t, 'close Socrates')
    t = S.t('The sky above the courtyard is turning grey')
    if t is not None:
        S.prop('sky', t, frm='BEFORE DAWN', to='GREY', dur=8.0)
        S.cam(t, 'high')
    t = S.t('A long silence. Adeimantus has fallen asleep')
    if t is not None:
        S.sleep('Adeimantus', S.t('A long silence', word='Adeimantus'))
        S.sleep('Glaucon', S.t('A long silence', word="Glaucon's eyes"))
        S.cam(t, 'wide')
    if rise is not None:
        S.place('Socrates', rise + 0.2, ('stand', 'before_corner', 'Julian'), 'move')
        S.place('Julian', rise + 3.0, ('stand', 'corner', 'Socrates'), 'move')
        S.cam(rise, 'follow Socrates')
        S.look('Julian', rise + 1.0, 'Socrates')
    t = S.t('~raising a hand gently')
    if t is not None:
        S.gesture('raise_gently', 'Socrates', t, S.end('~raising a hand gently', 0.4))
    t = S.t('~he glances back at the sleeping')
    if t is not None:
        S.look('Socrates', t, 'mid', t + 1.8)
        S.look('Socrates', t + 1.8, 'wall', t + 3.6)
    t = S.t("He folds Julian's fingers over the ring")
    if t is not None:
        S.gesture('hold_hand', 'Socrates', t + 0.2, S.end("He folds Julian's fingers", 1.2), other='Julian')
        S.cam(t, 'ots Socrates,Julian')
    t = S.t('~smiling')
    if t is not None:
        S.expr('Julian', S.t('Maintain the mirror'), S.end('Maintain the mirror', 1.0), 'warm', 0.8)
    t = S.t('Julian turns the ring a full circle')
    if t is not None:
        e = S.end('Julian turns the ring a full circle')
        S.vanish('Julian', t + 1.0, e - 0.2)
        S.place('Julian', e, ('away',))
        S.cam(t, 'close Julian')
    t = S.t('Socrates stands alone among the sleepers')
    if t is not None:
        S.cam(t, 'wide')
        tt = S.t('Socrates stands alone', word='The first ray')
        S.prop('sky', tt - 0.5, frm='GREY', to='SUNRISE', dur=3.0)
        S.cam(tt, 'chair')
    lounge = S.t('The same grey-gold light')
    if lounge is not None:
        S.scene(lounge - 0.2, 'lounge', 'INDOOR')
        for w in list(DAWN) + ['Socrates']:
            if w in S.places:
                S.place(w, lounge - 0.2, ('away',))
        import staging4_lounge
        staging4_lounge.ending(S, lounge)


def seq1(S):
    import staging4_lounge
    staging4_lounge.opening(S)


def stage(seq, S, i0, i1):
    {1: seq1, 2: seq2, 3: seq3, 4: seq4, 5: seq5, 6: seq6, 7: seq7}[seq](S)
