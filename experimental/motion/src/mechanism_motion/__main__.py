import argparse,json,os,tempfile
from pathlib import Path
import torch
from .engine import solve
def main():
    parser=argparse.ArgumentParser(description='Experimental fixed-phase six-bar pose/derivative solver')
    parser.add_argument('input',type=Path);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--seed',type=int,default=580000000);parser.add_argument('--threads',type=int,default=1);parser.add_argument('--baseline',action='store_true',help='Use the original random fallback for comparison')
    args=parser.parse_args()
    if not 1<=args.threads<=64:parser.error('--threads must be from 1 through 64')
    try:
        if args.input.resolve()==args.output.resolve() or (args.output.exists() and args.input.samefile(args.output)):
            parser.error('Input and output must be different files')
        payload=json.loads(args.input.read_text(encoding='utf-8'))
    except (ValueError,OSError) as exc:parser.error(str(exc))
    torch.set_num_threads(args.threads)
    try:result=solve(payload,args.seed,use_chooser=not args.baseline)
    except (ValueError,OSError) as exc:parser.error(str(exc))
    temporary=None
    try:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=args.output.parent,prefix=args.output.name+'.',suffix='.tmp',delete=False) as stream:
            temporary=Path(stream.name)
            stream.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
        os.replace(temporary,args.output)
    except OSError as exc:parser.error(str(exc))
    finally:
        if temporary is not None:temporary.unlink(missing_ok=True)
    print(json.dumps(dict(qualified=result['qualified'],objective_evaluations=result['objective_evaluations'],status=result['status'])))
if __name__=='__main__':main()
