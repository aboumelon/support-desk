import { mkdir, readFile, writeFile } from "node:fs/promises";
import Ajv from "ajv";
import standalone from "ajv/dist/standalone/index.js";
import { format } from "prettier";

const schema = JSON.parse(
  await readFile(
    new URL("../../../contracts/realtime.schema.json", import.meta.url),
    "utf8",
  ),
);
const ajv = new Ajv({
  strict: false,
  validateFormats: false,
  code: { source: true, esm: true, lines: true },
});
const imports = new Map();
const code = standalone(ajv, ajv.compile(schema)).replace(
  /require\("(ajv\/dist\/runtime\/[\w-]+)"\)\.default/g,
  (_, path) => {
    if (!imports.has(path)) imports.set(path, `runtime${imports.size}`);
    const name = imports.get(path);
    // Ajv emits CommonJS runtime bindings even in standalone ESM. Normalize its
    // static helper imports for both native Node ESM and Vite's CJS interop.
    return `(${name}.default ?? ${name})`;
  },
);
if (/\brequire\s*\(/.test(code)) {
  throw Error("Unsupported standalone runtime binding; update the generator");
}
const header =
  "// Generated from contracts/realtime.schema.json. Do not edit.\n";
const bindings = [...imports].map(
  ([path, name]) => `import ${name} from ${JSON.stringify(path + ".js")};`,
);
const directory = new URL("../src/generated/", import.meta.url);
await mkdir(directory, { recursive: true });
await writeFile(
  new URL("realtime.validator.mjs", directory),
  await format(header + bindings.join("\n") + "\n" + code, { parser: "babel" }),
);
await writeFile(
  new URL("realtime.validator.d.mts", directory),
  await format(
    header +
      "declare const validate: (data: unknown) => boolean;\n" +
      "export { validate };\nexport default validate;\n",
    { parser: "typescript" },
  ),
);
