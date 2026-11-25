#!/usr/bin/env python3
"""Checks that every SPIR-V blob in compiled/ converts to WGSL, as the browser's WebGPU backend needs.

Each compiled/<name>.h holds a <name>_spirv array. This extracts it, runs `naga` on it and reports the shaders that do
not convert. WGSL has no arrays between shader stages and no two resources on one (group, binding), so this catches the
first at the source.

SDL_GPU's shader convention puts a texture and its sampler on the same (set, binding), which naga rejects. A WebGPU
backend has to assign them separate bindings, so for this check only, the later resource of each clashing pair is moved
to binding + 16 before naga looks at it. The compiled blobs are not changed.

    cargo install naga-cli
    python3 check_wgsl.py <out_dir> [naga_path]

<out_dir> receives the .spv and .wgsl files. Exits 1 if any shader fails.
"""

import os
import re
import struct
import subprocess
import sys

current_dir = os.path.dirname(os.path.realpath(__file__))
compiled_dir = os.path.join(current_dir, "compiled")


def split_clashing_bindings(spirv):
    words = list(struct.unpack("<%dI" % (len(spirv) // 4), spirv))
    sets, bindings, seen = {}, {}, set()
    i = 5
    while i < len(words):
        opcode, count = words[i] & 0xFFFF, words[i] >> 16
        if opcode == 71 and words[i + 2] == 34:  # OpDecorate DescriptorSet
            sets[words[i + 1]] = words[i + 3]
        if opcode == 71 and words[i + 2] == 33:  # OpDecorate Binding
            bindings[words[i + 1]] = i + 3
        i += count
    for variable in sorted(bindings):
        key = (sets.get(variable), words[bindings[variable]])
        if key in seen:
            words[bindings[variable]] += 16
        seen.add(key)
    return struct.pack("<%dI" % len(words), *words)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 check_wgsl.py <out_dir> [naga_path]")
        return 1
    out_dir = sys.argv[1]
    naga = sys.argv[2] if len(sys.argv) > 2 else "naga"
    os.makedirs(out_dir, exist_ok=True)

    failed = 0
    names = sorted(f[:-2] for f in os.listdir(compiled_dir) if f.endswith(".h") and f != "ShadersCompiled.h")
    for name in names:
        with open(os.path.join(compiled_dir, name + ".h"), encoding="utf-8") as f:
            match = re.search(r"_spirv\[\] = \{(.*?)\};", f.read(), re.S)
        spirv = bytes(int(x, 16) for x in re.findall(r"0x([0-9A-Fa-f]{2})", match.group(1)))
        spv_path = os.path.join(out_dir, name + ".spv")
        with open(spv_path, "wb") as f:
            f.write(split_clashing_bindings(spirv))
        result = subprocess.run([naga, spv_path, os.path.join(out_dir, name + ".wgsl")], capture_output=True, text=True)
        if result.returncode != 0:
            failed += 1
            detail = (result.stderr.strip().splitlines() or ["naga failed"])[0]
            print("FAIL {}: {}".format(name, detail))
            print("\t" + "\n\t".join(result.stderr.strip().splitlines()[1:3]))
        else:
            print("ok   " + name)
    print("\n{} of {} shaders convert.".format(len(names) - failed, len(names)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
