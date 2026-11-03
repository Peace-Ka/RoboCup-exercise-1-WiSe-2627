"""I evaluate the integrated striker through the unchanged course runner.

From the repository root, with rsoccer activated:
  python scripts/evaluate_readiness.py 1
  python scripts/evaluate_readiness.py 1 --fixed

The first command runs idle/rule/Q-table opponents. --fixed runs the Q-table
comparison with learning disabled. Each match uses a fresh strategy instance.
"""
import argparse
import collections
import contextlib
import json
from math import hypot
from pathlib import Path
import re
import time
import subprocess
import hashlib
import sys

ROOT=Path(__file__).resolve().parents[1]
LOCAL_SOURCE=ROOT/'src'
if not LOCAL_SOURCE.exists():
    LOCAL_SOURCE=ROOT/'ssl_strategy_api-exercise1/src'
sys.path.insert(0,str(LOCAL_SOURCE))

from ssl_strategy_api.run_demos.run_rsoccer_exercise1_eval import run_evaluation
from ssl_strategy_api.strategies.striker import StrikerStrategy, FIRE_RANGE_M
from ssl_strategy_api.strategies.goalkeeper import GoalkeeperStrategy
from ssl_strategy_api.strategies.goalkeeper_rl import QTableGoalkeeperStrategy
from ssl_strategy_api.strategies.idle_goalkeeper_rl import IdleGoalkeeperStrategy

class ObservedStriker(StrikerStrategy):
    def __init__(self, learn):
        self.AIM_LEARNING=learn
        super().__init__()
        self.counts=collections.Counter()
        self.decision_ms=[]
    def decide(self,state,config):
        start=time.perf_counter()
        result=super().decide(state,config)
        self.decision_ms.append((time.perf_counter()-start)*1000)
        self.counts['phase_'+self.phase]+=1
        robot=state.robots_blue.get(0)
        for intent in result.values():
            if hypot(intent.vx_mps,intent.vy_mps)>2.00000001 or abs(intent.angular_velocity_rad_s)>3.00000001:
                self.counts['motion_limit_violations']+=1
            if intent.kick_speed_mps:
                self.counts['kick_requests']+=1
                if robot is not None and state.ball is not None and robot.infrared is not True:
                    distance=hypot(robot.x_m-state.ball.x_m,robot.y_m-state.ball.y_m)
                    if distance>FIRE_RANGE_M+1e-9:
                        self.counts['out_of_range_kicks']+=1
            if self._carrying and self.phase==self.CONTACT and hypot(intent.vx_mps,intent.vy_mps)>0:
                self.counts['carrying_motion_frames']+=1
                if not intent.dribbler:
                    self.counts['carrying_without_dribbler']+=1
        return result

parser=argparse.ArgumentParser()
parser.add_argument('seed',type=int)
parser.add_argument('--fixed',action='store_true')
parser.add_argument('--duration-seconds',type=float,default=90)
parser.add_argument('--output-dir',type=Path,default=Path('results/submission_readiness'))
args=parser.parse_args()
commit=subprocess.run(['git','rev-parse','HEAD'],capture_output=True,text=True)
source_commit=commit.stdout.strip() if commit.returncode==0 else 'unknown (extracted archive)'
source=Path(__file__).resolve().parents[1]/'ssl_strategy_api-exercise1/src/ssl_strategy_api/strategies'
if not source.exists():
    source=Path(__file__).resolve().parents[1]/'src/ssl_strategy_api/strategies'
strategy_sha256={name:hashlib.sha256((source/(name+'.py')).read_bytes()).hexdigest()
                 for name in ['movement','striker','aiming']}
opponents={'qtable':QTableGoalkeeperStrategy} if args.fixed else {'idle':IdleGoalkeeperStrategy,'rule':GoalkeeperStrategy,'qtable':QTableGoalkeeperStrategy}
for name,cls in opponents.items():
    mode='fixed' if args.fixed else 'learned'
    label=f'{name}-{mode}-seed{args.seed}'
    root=args.output_dir
    root.mkdir(parents=True,exist_ok=True)
    striker=ObservedStriker(not args.fixed)
    started=time.monotonic()
    with (root/(label+'.log')).open('w',encoding='utf-8') as log,contextlib.redirect_stdout(log):
        stats=run_evaluation(striker,cls(),duration_seconds=args.duration_seconds,render=False,seed=args.seed)
    elapsed=time.monotonic()-started
    text=(root/(label+'.log')).read_text(encoding='utf-8')
    scores=re.findall(r'Blue Team (\d+) - Yellow Team (\d+)',text)
    blue,yellow=map(int,scores[-1]) if scores else (0,0)
    steps=re.findall(r'finished: [0-9.]+s, (\d+) steps',text)
    timings=sorted(striker.decision_ms)
    model=striker._aimer.model
    result=dict(source_commit=source_commit,strategy_sha256=strategy_sha256,opponent=name,aiming=mode,seed=args.seed,
                duration_requested_s=args.duration_seconds,elapsed_including_setup_s=round(elapsed,3),
                steps=int(steps[-1]) if steps else None,blue_goals=blue,yellow_goals=yellow,
                official_stats=stats,observations=dict(striker.counts),
                decision_p95_ms=round(timings[int(.95*(len(timings)-1))],3),
                decision_max_ms=round(max(timings),3),
                learned_model=dict(gain=model.gain,v_max_mps=model.v_max_mps,y_limit_m=model.y_limit_m,
                                   ball_speed_mps=model.ball_speed_mps,keeper_samples=len(model.samples)))
    (root/(label+'.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result),flush=True)
