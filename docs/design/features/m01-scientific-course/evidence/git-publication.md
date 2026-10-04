# Original-byte publication verification

MAIN's explicit seam resolution was persisted BEFORE changes in01a2bdf. Only the exact approved NEW SVG-path rule was appended to .gitattributes:

`data/derived/m01-scientific-course/**/*.svg -text whitespace=-blank-at-eol,cr-at-eol`

No original SVG/JSON/PNG byte, scientific field, receipt, exporter, old path or global rule changed. This is preservation of original generated records, not normalizing them and inventing replacement hashes. Earlier failed staging, whitespace and source/UI tests remain recorded in numerical-checkpoint.md.

After re-staging, actual verification read EACH of33 blobs using git show :data/derived/m01-scientific-course/<case>/<basename>. Every blob equalled both its original ignored-export bytes and working bytes; its actual length/SHA256 matched the eight-key index. Each actual exporter receipt had already bound its ten original members. All33 passed; index blob also matched its unchanged10476 working bytes, SHA256 e2d6752f235050cab1571f2ed33588586744074d6ec4aaa650ff9e6bb13c97ba. git diff --cached --check now actually PASS.

For the previously failing case0 maps-light.svg, Git now retains the original413984df11e687855389be854f60820f9bf9f87abda2b45ffcc748b3335ca011 rather than the normalized454bef... value. Source/scientific identity and actual controls are unchanged. This resolves the publication seam only; generated records remain pending MAIN independent acceptance and whole-course/product QA.

Own frontend toolchain preflight: existing Node v24.14.1 SHA256 58e74bf02fc5bbacc41dcb8bef089961cd5bdd37830b87784e4fc624d145d1f; npm11.11.0, existing npm-cli.js SHA256 3ce7cba6f5128dd5f54c98b6a5036b0f850496878cc2e21044b675fe3c594e3e. Committed package-lock.json88447 bytes SHA256 db7820b708855821124506150278af83ce1b31c3ec90e3316047dbbee48e6853 matched HEAD bytes before setup; node_modules was absent. MAIN authorizes only npm ci --ignore-scripts in this owned frontend. No dependency/lock/global/shared/runtime/browser installation change is authorized. Setup/compile outcomes must be recorded separately after actual execution.
