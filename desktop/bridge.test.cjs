const { test } = require("node:test");
const assert = require("node:assert/strict");
const { validate, Backend } = require("./bridge.cjs");
test("IPC command surface is bounded", () => {
  validate("state", {});
  validate("set_setting", { name: "goal", value: 4100 });
  for (const name of ["shell", "reset", "raw_write", "install_adapter"])
    assert.throws(() => validate(name, {}));
  assert.throws(() => validate("state", []));
  assert.throws(() => validate("notify", { text: "x".repeat(9000) }));
});
test("backend routes responses and rejects after process exit", async () => {
  const code = `const r=require('readline').createInterface({input:process.stdin});r.on('line',l=>{const m=JSON.parse(l);console.log(JSON.stringify(m.command==='fail'?{id:m.id,error:{message:'safe error'}}:{id:m.id,result:m.args}));});`;
  const backend = new Backend(process.execPath, ["-e", code]);
  assert.deepEqual(await backend.request("echo", { value: 7 }), { value: 7 });
  await assert.rejects(backend.request("fail"), /safe error/);
  backend.close();
  await new Promise((resolve) => backend.child.on("exit", resolve));
  await assert.rejects(backend.request("echo"), /unavailable/);
});
