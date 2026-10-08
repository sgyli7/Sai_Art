"""Generate reference geometry locally; record the exact Comfy graph and output.

No text-to-image or texture synthesis. The raw generated mesh remains intact.
The resulting geometry is a Blender reconstruction input, not an accepted asset.
"""
from pathlib import Path
import asyncio
import aiohttp
import hashlib
import json
import shutil
import time
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
COMFY = Path('/home/ethan/Softwares/ComfyUI')
PIPELINE = Path('/home/ethan/Softwares/ai-3d-local/workflows/pixal3d_image_to_3d_api.json')
REFERENCE = Path('/home/ethan/Projects/Sai_Art/docs/uri_style/gorilla_v0_1/reference_rebuild_r4/references/primary_user_reference.jpg')
BASE = 'http://127.0.0.1:8188'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def request(path, data=None):
    if data is None:
        req = urllib.request.Request(BASE + path)
    else:
        req = urllib.request.Request(BASE + path, data=json.dumps(data).encode(),
                                     headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def write(name, value):
    (ROOT / 'source' / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


async def main():
    for name in ('source', 'references', 'generated', 'images'):
        (ROOT / name).mkdir(parents=True, exist_ok=True)
    shutil.copy2(REFERENCE, ROOT / 'references' / 'primary_user_reference.jpg')
    image_name = 'gorilla_v02_reference_geometry.jpg'
    shutil.copy2(REFERENCE, COMFY / 'input' / image_name)
    graph = json.loads(PIPELINE.read_text())['prompt']
    # Take geometry only. Do not generate texture or replace the reference.
    keep = {'load_image', 'bg_model', 'bg', 'crop', 'clip', 'unet', 'shape_vae',
            'empty', 'cfg_ss', 'rescale_ss', 'shift_ss', 'cfg_sh', 'rescale_sh',
            'moge_model', 'moge', 'fov', 'cond', 'ks_ss', 'decode_ss',
            'shape_stage', 'ks_sh', 'upsample', 'ks_hr', 'decode_shape', 'save_raw'}
    graph = {key: value for key, value in graph.items() if key in keep}
    graph['load_image']['inputs']['image'] = image_name
    graph['save_raw']['inputs']['filename_prefix'] = 'gorilla_v02/reference_raw_geometry'
    graph['save_conditioning'] = {'class_type': 'SaveImage', 'inputs': {
        'images': ['crop', 0], 'filename_prefix': 'gorilla_v02/actual_geometry_input'}}
    write('pixal3d_geometry_workflow.json', {'prompt': graph})
    metadata = {
        'revision': 'gorilla_v02_reference_3d_g1',
        'generator': 'Local ComfyUI Pixal3D INT8',
        'reference_sha256': sha(REFERENCE),
        'workflow_sha256': sha(ROOT / 'source' / 'pixal3d_geometry_workflow.json'),
        'upstream_workflow_sha256': sha(PIPELINE),
        'text_prompt': None, 'imagegen_used': False, 'texture_generation_used': False,
        'reference_geometry_accepted': False, 'ready_for_handoff': False,
        'model_frame': 'glTF Y-up; orientation and physical scale require Blender calibration',
        'reference_scope': 'One cropped photo. Visible geometry is the reconstruction target; hidden geometry inferred by the generator requires review.',
        'weights': []
    }
    for path in (COMFY / 'models' / 'diffusion_models' / 'pixal3d_int8_convrot.safetensors',
                 COMFY / 'models' / 'vae' / 'trellis_2_shape_vae_bf16.safetensors',
                 COMFY / 'models' / 'clip_vision' / 'dino_v3_L_naf_fp32.safetensors',
                 COMFY / 'models' / 'geometry_estimation' / 'moge_2_vitl_normal_fp16.safetensors',
                 COMFY / 'models' / 'background_removal' / 'birefnet.safetensors'):
        metadata['weights'].append({'path': str(path), 'bytes': path.stat().st_size,
                                    'sha256': sha(path)})
    client = str(uuid.uuid4())
    started = time.time()
    async with aiohttp.ClientSession() as session, session.ws_connect(
            'ws://127.0.0.1:8188/ws?clientId=' + client,
            max_msg_size=32 * 1024 * 1024) as socket:
        submitted = request('/prompt', {'prompt': graph, 'client_id': client})
        metadata.update(prompt_id=submitted['prompt_id'], client_id=client, status='running')
        write('generation_record.json', metadata)
        prompt_id = metadata['prompt_id']
        print('GENERATION_QUEUED', prompt_id, flush=True)
        last_progress = None
        while True:
            try:
                raw = await asyncio.wait_for(socket.receive(), timeout=45)
            except TimeoutError:
                print('GENERATION_RUNNING elapsed_seconds=' + str(int(time.time()-started)), flush=True)
                history = request('/history/' + prompt_id)
                if prompt_id in history and history[prompt_id].get('status', {}).get('completed'):
                    break
                continue
            if raw.type != aiohttp.WSMsgType.TEXT:
                continue
            event = json.loads(raw.data)
            kind, data = event.get('type'), event.get('data', {})
            if data.get('prompt_id', prompt_id) != prompt_id:
                continue
            if kind == 'executing':
                node = data.get('node')
                if node is None:
                    break
                print('GENERATION_STAGE', node, graph.get(node, {}).get('class_type'), flush=True)
                last_progress = None
            elif kind == 'progress':
                maximum = data.get('max', 0)
                percent = int(100 * data.get('value', 0) / maximum) if maximum else 0
                bucket = percent // 20
                if bucket != last_progress or percent == 100:
                    print('GENERATION_PROGRESS', percent, flush=True)
                    last_progress = bucket
            elif kind == 'execution_error':
                metadata.update(status='failed', error=data,
                                elapsed_seconds=time.time()-started)
                write('generation_record.json', metadata)
                raise RuntimeError(str(data.get('exception_message', data))[:2000])
        history = request('/history/' + prompt_id)[prompt_id]
        write('comfy_execution_history.json', history)
        outputs = []
        for node_id, output in history.get('outputs', {}).items():
            for output_type in ('3d', 'images'):
                for item in output.get(output_type, []):
                    source = COMFY / 'output' / item.get('subfolder', '') / item['filename']
                    destination = ROOT / ('generated' if output_type == '3d' else 'references') / source.name
                    shutil.copy2(source, destination)
                    outputs.append({'node': node_id, 'file': str(destination.relative_to(ROOT)),
                                    'bytes': destination.stat().st_size, 'sha256': sha(destination)})
        metadata.update(status=history.get('status', {}).get('status_str'),
                        elapsed_seconds=time.time()-started, outputs=outputs)
        write('generation_record.json', metadata)
        print('GENERATION_FINISHED', json.dumps(outputs), flush=True)


if __name__ == '__main__':
    asyncio.run(main())
