"""Geometry-only image-to-3D from the user's complete foot reference.

No text-to-image step and no surface/texture synthesis. Visible foot geometry
is the reference; inferred hidden surfaces remain an unaccepted candidate.
"""
from pathlib import Path
import asyncio, json, hashlib, shutil, time, uuid, urllib.request
import aiohttp

ROOT=Path(__file__).resolve().parents[1]
COMFY=Path('/home/ethan/Softwares/ComfyUI')
REFERENCE=ROOT/'references/foot_reference_complete_foreheel.jpg'
BASE='http://127.0.0.1:8188'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def request(path,data=None):
    req=urllib.request.Request(BASE+path,data=None if data is None else json.dumps(data).encode(),
                              headers={} if data is None else {'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)
def write(name,data):
    (ROOT/'source'/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')

async def main():
    q=request('/queue')
    if q.get('queue_running') or q.get('queue_pending'):
        raise RuntimeError('ComfyUI already has queued work; no graph submitted.')
    image_name='gorilla_complete_foot_reference_s6.jpg'
    shutil.copy2(REFERENCE,COMFY/'input'/image_name)
    graph=json.loads((ROOT/'source/pixal3d_geometry_workflow.json').read_text())['prompt']
    graph['load_image']['inputs']['image']=image_name
    graph['save_raw']['inputs']['filename_prefix']='gorilla_v02/complete_foot_reference_s6'
    graph['save_conditioning']['inputs']['filename_prefix']='gorilla_v02/complete_foot_reference_input_s6'
    write('pixal3d_complete_foot_workflow_s6.json',{'prompt':graph})
    old_record=json.loads((ROOT/'source/generation_record.json').read_text())
    metadata={
        'revision':'complete_foot_reference_geometry_s6',
        'reference':str(REFERENCE.relative_to(ROOT)),
        'reference_sha256':sha(REFERENCE),
        'workflow_sha256':sha(ROOT/'source/pixal3d_complete_foot_workflow_s6.json'),
        'generator':'Local ComfyUI Pixal3D INT8; installed unchanged weights',
        'weights_identity_from_existing_generation_record':old_record.get('weights',[]),
        'text_prompt':None,'imagegen_used':False,'texture_generation_used':False,
        'scope':'Extract complete toe/ankle/heel geometry after actual native inspection; reference leg is not adopted as Gorilla thigh geometry.',
        'geometry_accepted':False,'engineering_ready':False,
    }
    started=time.time();client=str(uuid.uuid4())
    async with aiohttp.ClientSession() as session,session.ws_connect(
            'ws://127.0.0.1:8188/ws?clientId='+client,max_msg_size=32*1024*1024) as socket:
        submitted=request('/prompt',{'prompt':graph,'client_id':client})
        metadata.update(prompt_id=submitted['prompt_id'],client_id=client,status='running')
        write('complete_foot_generation_record_s6.json',metadata)
        prompt_id=metadata['prompt_id'];last=None
        print('FOOT_REFERENCE_GEOMETRY_QUEUED',prompt_id,flush=True)
        while True:
            try:raw=await asyncio.wait_for(socket.receive(),timeout=45)
            except TimeoutError:
                print('FOOT_GEOMETRY_RUNNING',int(time.time()-started),flush=True)
                history=request('/history/'+prompt_id)
                if prompt_id in history and history[prompt_id].get('status',{}).get('completed'):break
                continue
            if raw.type!=aiohttp.WSMsgType.TEXT:continue
            event=json.loads(raw.data);kind=event.get('type');data=event.get('data',{})
            if data.get('prompt_id',prompt_id)!=prompt_id:continue
            if kind=='executing':
                node=data.get('node')
                if node is None:break
                print('FOOT_GEOMETRY_STAGE',node,graph.get(node,{}).get('class_type'),flush=True)
                last=None
            elif kind=='progress':
                maximum=data.get('max',0);percent=int(100*data.get('value',0)/maximum) if maximum else 0
                bucket=percent//20
                if bucket!=last or percent==100:
                    print('FOOT_GEOMETRY_PROGRESS',percent,flush=True);last=bucket
            elif kind=='execution_error':
                metadata.update(status='failed',error=data,elapsed_seconds=time.time()-started)
                write('complete_foot_generation_record_s6.json',metadata)
                raise RuntimeError(str(data.get('exception_message',data))[:2000])
        history=request('/history/'+prompt_id)[prompt_id]
        write('complete_foot_execution_history_s6.json',history)
        outputs=[]
        for node,out in history.get('outputs',{}).items():
            for typ in ('3d','images'):
                for item in out.get(typ,[]):
                    src=COMFY/'output'/item.get('subfolder','')/item['filename']
                    dst=ROOT/('generated' if typ=='3d' else 'references')/src.name
                    shutil.copy2(src,dst)
                    outputs.append({'node':node,'file':str(dst.relative_to(ROOT)),
                                    'bytes':dst.stat().st_size,'sha256':sha(dst)})
        metadata.update(status=history.get('status',{}).get('status_str'),
                        elapsed_seconds=time.time()-started,outputs=outputs)
        write('complete_foot_generation_record_s6.json',metadata)
        print('FOOT_REFERENCE_GEOMETRY_FINISHED',json.dumps(outputs),flush=True)

if __name__=='__main__':asyncio.run(main())
