#!/usr/bin/env python3
"""Build a separate Termius 9.37.2 archive with running commands in tab titles."""
import hashlib
import json
from pathlib import Path
import struct

SUPPORTED_VERSION = "9.37.2"
UI = 'ui-process/assets/ui-process-4168589b.js'
SHARED = 'ui-process/assets/reconnectSaga-c10a1975.js'
FISH = 'out/shell-integration/xdg_data/fish/vendor_conf.d/termius.fish'

HELPER = r'''function termiusDynamicTabTitle(title,terminals,editing){
if(editing)return title;
const terminal=terminals.find(t=>t.isActive)||terminals[0];
if(!terminal)return title;
const local=(terminal.protocol||terminal.connectionProtocol)==="local";
const cwd=terminal.cwd||"~",idleTitle=local?cwd:title;
if(terminal.isDisconnected||terminal.disconnectTimestamp!=null||terminal.startupContextRestorationState==="restoring")return idleTitle;
if(terminal.connectionProcess!=="succeeded")return idleTitle;
const command=terminal.activeCommand;
if(!command||command.endTimestamp!=null||command.exitCode!=null||command.isRestorationCommand||typeof command.command!=="string")return idleTitle;
// Termius marks commands lasting 500 ms; keep fast local commands from flashing.
if(local&&!command.isDurational)return idleTitle;
const input=command.command.replace(/[\x00-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069]/g," ").replace(/\s+/g," ").trim();
// Supported snippet form: one leading cd, followed by && and the command.
const text=input.replace(/^cd\s+(?:--\s+)?(?:"(?:\\.|[^"\\])*"|'[^']*'|(?:\\.|[^\s;&|"'\\])+)\s*&&\s*/,"").replace(/\s+-.*$/,"");
if(!text)return idleTitle;
const directory=cwd.replace(/\/+$/,"").split("/").pop()||"/";
const label=Array.from(text);return (local?directory:title)+" · "+(label.length>60?label.slice(0,59).join("")+"…":text);
}
function termiusTabUsesPath(title,terminals){
const terminal=terminals.find(t=>t.isActive)||terminals[0];
return !!terminal&&(terminal.protocol||terminal.connectionProtocol)==="local"&&title===(terminal.cwd||"~");
}
'''


def replace_once(text, before, after):
    count = text.count(before)
    if count != 1:
        raise RuntimeError(f'Unsupported Termius bundle: expected one anchor, got {count}: {before[:100]}')
    return text.replace(before, after, 1)


def entries(directory, prefix=''):
    for name, item in directory.get('files', {}).items():
        path = f'{prefix}/{name}' if prefix else name
        if 'files' in item:
            yield from entries(item, path)
        else:
            yield path, item


def build(source: Path, target: Path, check_dir: Path | None = None):
    """Validate and patch an installed archive into a separate destination."""
    if source.resolve() == target.resolve():
        raise RuntimeError("Source and target must be different archives")
    raw = source.read_bytes()
    _, header_size, _, json_size = struct.unpack_from('<4I', raw)
    header = json.loads(raw[16:16 + json_size])
    base = 8 + header_size
    files = dict(entries(header))
    def read(path):
        item = files[path]
        if item.get('unpacked'):
            return Path(str(source) + '.unpacked', path).read_bytes()
        start = base + int(item['offset'])
        return raw[start:start + item['size']]
    version = json.loads(read('package.json'))['version']
    if version != SUPPORTED_VERSION:
        raise RuntimeError(f'This patch is checked for 9.37.2, found {version}')
    shared = read(SHARED).decode()
    shared = replace_once(shared,
        'mapTerminal=({terminal:er,multiplayerConnectionProcess:tr})=>({id:er.id,',
        'mapTerminal=({terminal:er,multiplayerConnectionProcess:tr})=>({cwd:er.cwd,activeCommand:er.activeCommand,isActive:er.isActive,startupContextRestorationState:er.startupContextRestorationState,id:er.id,')
    ui = read(UI).decode()
    # Keep saved titles and drag data intact; decorate only rendered labels.
    ui = replace_once(ui,
        'c=W(f=>rq(f,e)),u={tabId:e.id,title:e.title,',
        'c=W(f=>rq(f,e)),dynamicTitle=termiusDynamicTabTitle(e.title,l,e.isEditingTitle),u={tabId:e.id,title:dynamicTitle,')
    ui = replace_once(ui,
        'return d(Ip,{...u,...p,customIcon:m,',
        'return d(Ip,{...u,...p,title:dynamicTitle,customIcon:m,')
    ui = replace_once(ui,
        'tabId:u,title:p,isEditingTitle:f,hasUnreadOutput:!!m,',
        'tabId:u,title:termiusDynamicTabTitle(p,[e],f),isEditingTitle:f,hasUnreadOutput:!!m,')
    ui = replace_once(ui,
        'className:b.headingTitle,children:t}',
        'className:b.headingTitle,children:termiusDynamicTabTitle(t,[n],n.isEditingTitle)}')
    # CSS chooses the ellipsis edge at the actual available tab width.
    ui = replace_once(ui,
        'children:d(Hy,{...p,shouldScrollIntoView:A,',
        'children:d(Hy,{...p,tailEllipsis:termiusTabUsesPath(p.title,t),shouldScrollIntoView:A,')
    ui = replace_once(ui,
        'd(oRe,{defaultValue:t,title:t,className:y.title,',
        'd(oRe,{defaultValue:t,title:t,tailEllipsis:n.tailEllipsis,className:y.title,')
    ui = replace_once(ui,
        'oRe=({defaultValue:n,title:e,onChange:t,onOverflow:o,editable:r,className:i})=>',
        'oRe=({defaultValue:n,title:e,onChange:t,onOverflow:o,editable:r,className:i,tailEllipsis:tailEllipsis=!1})=>')
    ui = replace_once(ui,
        'd("div",{ref:C,className:f.title,children:e})',
        'd("div",{ref:C,className:f.title,style:tailEllipsis?{direction:"rtl",textAlign:"left"}:void 0,children:tailEllipsis?d("bdi",{dir:"ltr",children:e}):e})')
    # Function declarations are hoisted, so the helper can live at module end.
    ui += '\n' + HELPER
    fish = replace_once(read(FISH).decode(),
        'function _termius_update_cwd --on-event fish_prompt\n',
        '# Report cd immediately, including cd && a long-running command.\n'
        'function _termius_dynamic_tabs_cwd_changed --on-variable PWD\n'
        '\t_termius_current_cwd\n'
        'end\n\n'
        'function _termius_update_cwd --on-event fish_prompt\n')
    # Fish splits multiline command substitutions into separate printf arguments.
    # Join base64's wrapped lines so each command is sent in one OSC message.
    fish = replace_once(fish,
        'builtin echo -n "$argv[1]" | command base64',
        'builtin printf "%s" "$argv[1]" | command base64 | string join ""')
    replacements = {UI: ui.encode(), SHARED: shared.encode(), FISH: fish.encode()}
    payloads = []
    offset = 0
    for path, item in entries(header):
        if path not in replacements and ('offset' not in item or item.get('unpacked')):
            continue
        data = replacements.get(path)
        if data is None:
            start = base + int(item['offset'])
            data = raw[start:start + item['size']]
        if not item.get('unpacked'):
            item['offset'] = str(offset)
        item['size'] = len(data)
        if path in replacements and 'integrity' in item:
            integrity = item['integrity']
            if integrity.get('algorithm') != 'SHA256':
                raise RuntimeError('Unsupported integrity algorithm')
            block = integrity['blockSize']
            integrity['hash'] = hashlib.sha256(data).hexdigest()
            integrity['blocks'] = [hashlib.sha256(data[i:i + block]).hexdigest() for i in range(0, len(data), block)]
        if not item.get('unpacked'):
            payloads.append(data)
            offset += len(data)
    encoded = json.dumps(header, ensure_ascii=False, separators=(',', ':')).encode()
    padded = encoded + b'\0' * (-len(encoded) % 4)
    header_pickle = struct.pack('<II', 4 + len(padded), len(encoded)) + padded
    target.parent.mkdir(parents=True, exist_ok=True)
    pending = target.with_suffix('.asar.tmp')
    with pending.open('wb') as out:
        out.write(struct.pack('<II', 4, len(header_pickle)))
        out.write(header_pickle)
        for data in payloads:
            out.write(data)
    pending.replace(target)
    unpacked_fish = Path(str(target) + '.unpacked', FISH)
    unpacked_fish.parent.mkdir(parents=True, exist_ok=True)
    unpacked_fish.write_bytes(replacements[FISH])
    if check_dir is not None:
        check_dir.mkdir(parents=True, exist_ok=True)
        for path, data in replacements.items():
            if path.endswith('.js'):
                (check_dir / (Path(path).stem + '.mjs')).write_bytes(data)
        (check_dir / 'helper.js').write_text(HELPER)
    (target.parent / 'build.json').write_text(json.dumps({
        'version': version,
        'source_sha256': hashlib.sha256(raw).hexdigest(),
        'patched_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
        'changed_files': list(replacements),
    }, indent=2) + '\n')
    return version

