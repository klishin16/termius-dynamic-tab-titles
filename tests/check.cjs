const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const dir = process.argv[2].replace(/\/$/, '') + '/';
const ui = fs.readFileSync(dir + 'ui-process-4168589b.mjs', 'utf8');
const shared = fs.readFileSync(dir + 'reconnectSaga-c10a1975.mjs', 'utf8');
const context = vm.createContext({});
vm.runInContext(fs.readFileSync(dir + 'helper.js', 'utf8'), context);
const title = context.termiusDynamicTabTitle;
const running = {id: 'one', connectionProcess: 'succeeded', isActive: true,
  activeCommand: {command: 'npm run dev', startTimestamp: 1}};
assert.equal(title('server', [running]), 'server · npm run dev');
assert.equal(title('server', [{...running, activeCommand: {...running.activeCommand, exitCode: '0'}}]), 'server');
assert.equal(title('server', [{...running, activeCommand: {...running.activeCommand, endTimestamp: 2}}]), 'server');
assert.equal(title('server', [{...running, isDisconnected: true}]), 'server');
assert.equal(title('server', [{...running, connectionProcess: 'connecting'}]), 'server');
assert.equal(title('server', [{...running, startupContextRestorationState: 'restoring'}]), 'server');
assert.equal(title('server', [running], true), 'server');
assert.equal(title('workspace', [{...running, isActive: false}, {id: 'two', isActive: true}]), 'workspace');
assert.equal(title('server', []), 'server');
assert.equal(title('server', [{...running, activeCommand: {command: 'echo\nhello\x07'}}]), 'server · echo hello');
assert.equal(Array.from(title('', [{...running, activeCommand: {command: 'a'.repeat(100)}}])).length, 63);

// Exercise the actual patched mapper and tab component with React/Redux stubs.
const mapper = shared.slice(shared.indexOf('mapTerminal=') + 'mapTerminal='.length, shared.indexOf(',selectWorkspaces=', shared.indexOf('mapTerminal=')));
context.map = vm.runInContext('(' + mapper + ')', context);
const mapped = context.map({terminal: running});
assert.equal(mapped.activeCommand, running.activeCommand);
assert.equal(mapped.isActive, true);
context.state = {terminals: [mapped]};
Object.assign(context, {
  ln: () => false, UI: () => true, rq: () => false,
  oq: () => context.state.terminals,
  W: fn => fn(), d: (component, props) => ({component, props}),
  PLe: () => 5, LLe: () => false, Ip: 'Tab', au: 'horizontal', Ln: {horizontal: 'horizontal'},
});
const component = ui.slice(ui.indexOf('TLe=') + 4, ui.indexOf(',kLe=', ui.indexOf('TLe=')));
context.Tab = vm.runInContext('(' + component + ')', context);
const tab = Object.freeze({id: 'tab', title: 'server', tabType: 'terminalTab'});
assert.equal(context.Tab({tab, workspaces: {}}).props.title, 'server · npm run dev');
context.state.terminals = [context.map({terminal: {...running, activeCommand: {...running.activeCommand, exitCode: '0'}}})];
assert.equal(context.Tab({tab, workspaces: {}}).props.title, 'server');
context.state.terminals = [mapped];
assert.equal(context.Tab({tab: {...tab, isEditingTitle: true}, workspaces: {}}).props.title, 'server');
assert.equal(tab.title, 'server');

const local = {...running, connectionProtocol: 'local', cwd: '/home/user/projects/example',
  activeCommand: {...running.activeCommand, isDurational: true}};
context.state.terminals = [context.map({terminal: local})];
assert.equal(context.state.terminals[0].cwd, local.cwd);
assert.equal(context.Tab({tab: {...tab, title: 'Local Terminal'}, workspaces: {}}).props.title, 'example · npm run dev');
assert.equal(context.termiusTabUsesPath('example · npm run dev', context.state.terminals), false);
context.state.terminals = [context.map({terminal: {...local, activeCommand: {...local.activeCommand, exitCode: '0'}}})];
const idleTitle = context.Tab({tab: {...tab, title: 'Local Terminal'}, workspaces: {}}).props.title;
assert.equal(idleTitle, '/home/user/projects/example');
assert.equal(context.termiusTabUsesPath(idleTitle, context.state.terminals), true);
assert.equal(title('Local Terminal', [{...local, cwd: '/'}]), '/ · npm run dev');
assert.equal(title('Local Terminal', [{...local, cwd: '/tmp/example/'}]), 'example · npm run dev');
assert.equal(title('Local Terminal', [{...local, activeCommand: null}]), local.cwd);
assert.equal(title('Local Terminal', [{...local, activeCommand: null, cwd: undefined}]), '~');
assert.equal(title('server', [{...local, connectionProtocol: 'ssh'}]), 'server · npm run dev');

// Replay the real cd lifecycle: start, finish, then the new prompt's cwd.
const cd = {...local, activeCommand: {command: 'cd ../other', isDurational: false, startTimestamp: 3}};
const finishedCd = {...cd, activeCommand: {...cd.activeCommand, exitCode: '0', endTimestamp: 4}};
const changedDirectory = {...finishedCd, cwd: '/home/user/projects/other'};
for (const state of [cd, finishedCd, changedDirectory]) {
  context.state.terminals = [context.map({terminal: state})];
  const renderedTitle = context.Tab({tab: {...tab, title: 'Local Terminal'}, workspaces: {}}).props.title;
  assert.equal(renderedTitle, state.cwd);
  assert.equal(context.termiusTabUsesPath(renderedTitle, context.state.terminals), true);
}
assert.equal(title('Local Terminal', [{...local, activeCommand: {...local.activeCommand, isDurational: false}}]), local.cwd);
assert.equal(title('Local Terminal', [local]), 'example · npm run dev');
for (const [command, expected] of [
  ['npm run start:dev -- --watch', 'npm run start:dev'],
  ['cd ~/rootcode/swappa/backend && npm run start:dev', 'npm run start:dev'],
  ['cd ~/rootcode/swappa/backend && npm run start:dev -- --watch', 'npm run start:dev'],
  ['cd -- ~/rootcode/swappa/backend && npm run start:dev', 'npm run start:dev'],
  ['cd "/tmp/my project" && npm run dev', 'npm run dev'],
  ["cd '/tmp/a && b' && npm run dev", 'npm run dev'],
  ['cd /tmp/my\\ project && npm run dev', 'npm run dev'],
  ['echo "a && b"', 'echo "a && b"'],
  ['cd ~/rootcode/swappa/backend', 'cd ~/rootcode/swappa/backend'],
  ['docker compose up -d --build', 'docker compose up'],
  ['ls -la /tmp', 'ls'],
  ['node --inspect server.js', 'node'],
  ['ciadpi -Kt,h -d1 -s0+s -d3+s -s6+s -d9+s -s12+s -d15+s -s20+s -d25+s -s30+s -d35+s -An -Ku -a5 -s443+s -d80+s -d443+s -s80+s -s443+s -d53+s -s53+s -d443+s', 'ciadpi'],
  ['npm run start:dev', 'npm run start:dev'],
  ['my-tool some-file.js --output /tmp/file', 'my-tool some-file.js'],
]) {
  const activeCommand = {...local.activeCommand, command};
  assert.equal(title('Local Terminal', [{...local, activeCommand}]), 'example · ' + expected);
  assert.equal(title('server', [{...local, connectionProtocol: 'ssh', activeCommand}]), 'server · ' + expected);
}

// Check the real title renderer forwards the full path and uses left ellipsis.
const renderContext = vm.createContext({
  h: {useState: v => [v, () => {}], useRef: () => ({current: null}), useCallback: f => f, useEffect: () => {}},
  nRe: () => ({classes: {input: 'input', fullWidth: 'fullWidth', title: 'title'}, cx: (...s) => s.join(' ')}),
  yi: () => {}, d: (component, props) => ({component, props}),
});
const renderer = ui.slice(ui.indexOf('oRe=') + 4, ui.indexOf(',rRe=', ui.indexOf('oRe=')));
const render = vm.runInContext('(' + renderer + ')', renderContext);
const rendered = render({defaultValue: idleTitle, title: idleTitle, tailEllipsis: true});
const textNode = rendered.props.children.props.children;
assert.equal(textNode.props.style.direction, 'rtl');
assert.equal(textNode.props.children.props.dir, 'ltr');
assert.equal(textNode.props.children.props.children, idleTitle);
assert.equal(render({defaultValue: 'server', title: 'server'}).props.children.props.children.props.style, undefined);
console.log('PASS: local folder + command, idle path with left ellipsis, root paths, unchanged SSH titles, command lifecycle and actual tab rendering');
