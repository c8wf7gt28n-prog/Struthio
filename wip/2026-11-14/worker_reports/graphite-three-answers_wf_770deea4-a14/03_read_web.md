{
 "summary": "As of 12 Nov 2026 there is no model called \"Quinn\"; every search resolves to Alibaba's Qwen. Qwen 4 is announced but the 27B open-weight model is NOT released: only a cloud-only Qwen4-Max-Preview went live on 11 Nov 2026 (alias qwen4.0-max-preview, ends 25 Nov). The Qwen organisation on Hugging Face shows no Qwen4 repo; \"Qwen4-27B GGUF\" repos that exist are placeholders. The newest released 27B is Qwen3.8-27B (14 Aug 2026, Apache 2.0, 262,144 context, thinking on by default, ChatML template, Q4_K_M about 16.5-19.0 GB depending on publisher; bartowski 17.44 GB). The bundled llama.cpp b11669 (15 Oct 2026, v0.7.0) is newer than the builds used to quantise and run Qwen3.8-27B, so it should load it; it predates any Qwen4 weights and will probably be too old for Qwen4-27B. Nobody has published a 27B figure for the Radeon 680M; nearby data points suggest roughly 2-4 tokens/s generation, with Vulkan giving little or no generation gain over CPU at this size, and there is an open, unfixed RADV/680M device-loss bug in the b11669 range with two known workarounds.",
 "findings": [
  {
   "title": "Qwen4-27B is announced, not released; no weights, licence, specs or date",
   "detail": "Secondary sources agree Alibaba named four Qwen 4 tiers (Max, Plus, Flash, Qwen4-27B) at Apsara on 22 Sep 2026, with the 27B the only one called open; no licence, architecture, context length or release date given. Qwen4-Max-Preview went live 11 Nov 2026 02:00 UTC, cloud only (Token Plan), model ID qwen4-max-preview with alias qwen4.0-max-preview, switched off after 25 Nov; nothing said about weights. The Qwen org page on Hugging Face fetched today lists no repo containing 'Qwen4'; newest family is Qwen3.8. Unconfirmed rumours only for timing (inference from the 3.8 pattern: weights a week or two after the flagship). I found no Alibaba primary source for the Apsara lineup, only third-party write-ups.",
   "weight": "blocker",
   "where": "https://neurohive.io/en/news/qwen4-max/ ; https://www.yottalabs.ai/post/qwen-4-27b-release-date-specs-hardware-what-is-known-2026 ; https://huggingface.co/Qwen"
  },
  {
   "title": "Existing 'Qwen4-27B' GGUF repos are placeholders",
   "detail": "pirahansiah/Qwen4-27B-1bit-GGUF states 'Repository status: reserved placeholder \u2014 no weights are in this repository yet' and 'Qwen4-27B has not been published with open weights yet'. stealth-model/Qwen4 returned HTTP 401 and could not be inspected; it is not an Alibaba repo. Treat any Qwen4 GGUF as fake until Qwen/Qwen4-27B exists in the official org.",
   "weight": "important",
   "where": "https://huggingface.co/pirahansiah/Qwen4-27B-1bit-GGUF"
  },
  {
   "title": "No model named 'Quinn' found",
   "detail": "Two searches for 'Quinn' / 'Quinn 4.0' with 27B, GGUF, open weights returned only Qwen results. The 'qwen4.0-max-preview' alias shows Alibaba itself uses '4.0', which supports the working reading (Qwen 4.0, 27B, 4-bit). A negative cannot be proven, but nothing contradicts it.",
   "weight": "note",
   "where": "https://neurohive.io/en/news/qwen4-max/"
  },
  {
   "title": "Newest released 27B: Qwen/Qwen3.8-27B",
   "detail": "Released 14 Aug 2026 per Wikipedia (model card citation says only August 2026). Licence apache-2.0. 27B (safetensors panel says 28B incl. vision encoder); vision-language (image and video input). Context: '262,144 natively and extensible up to 1,000,000 tokens'. Hybrid architecture: 64 layers, 48 Gated DeltaNet linear-attention + 16 full attention; includes MTP (multi-token prediction) head. Recommended sampling: thinking temp 1.0 / top_p 0.95 / top_k 20; non-thinking temp 0.7 / top_p 0.80 / top_k 20 / presence_penalty 1.5.",
   "weight": "important",
   "where": "https://huggingface.co/Qwen/Qwen3.8-27B ; https://en.wikipedia.org/wiki/Qwen"
  },
  {
   "title": "Thinking is on by default at effort xhigh; this dominates wall time at laptop speeds",
   "detail": "Model card: 'Thinking mode is on by default and can be disabled per request' via chat_template_kwargs {\"enable_thinking\": false}; reasoning_effort accepts low / medium / xhigh (default xhigh; 'high' is reportedly rejected by the template and a top-level reasoning_effort field is reportedly ignored by llama.cpp, so pass it inside chat_template_kwargs). llama.cpp at tag b11669 documents: '-rea, --reasoning [on|off|auto]' (default auto), '--reasoning-budget N' (-1 unrestricted, 0 immediate end), '--chat-template-kwargs STRING', and Jinja enabled by default. Benchmarks found best GPQA results needed about 8k reasoning tokens and that xhigh 'can overthink'; at about 3 tokens/s, 8k reasoning tokens is roughly 45 minutes (my arithmetic). Use thinking off, low effort, or a reasoning budget for rehearsal.",
   "weight": "important",
   "where": "https://huggingface.co/Qwen/Qwen3.8-27B ; https://github.com/ggml-org/llama.cpp/blob/b11669/tools/server/README.md ; https://scriptable.com/posts/llama-cpp/run-qwen3-8-27b-llama-cpp-macos/ ; https://quesma.com/blog/qwen38-27b-quantizations-benchmarked/"
  },
  {
   "title": "Chat template family: ChatML with a <think> block",
   "detail": "bartowski's card shows <|im_start|>system ... <|im_end|> / <|im_start|>user / <|im_start|>assistant followed by <think>; the system turn is prefixed with 'Reasoning effort is set to xhigh. ...'. The template is embedded in the GGUF and needs the Jinja engine (default on at b11669). One guide warns the official template wraps every assistant turn in a think block, which misbehaves across turns if the shipped Jinja template is not used.",
   "weight": "minor",
   "where": "https://huggingface.co/bartowski/Qwen3.8-27B-GGUF ; https://dev.to/purpledoubled/run-qwen-38-27b-locally-real-gguf-sizes-the-kv-cache-trick-and-the-template-trap-114j"
  },
  {
   "title": "Q4_K_M file size differs by publisher: 16.5 to 19.0 GB",
   "detail": "bartowski Q4_K_M 17.44 GB (5.02 bpw); ggml-org Q4_K_M 19.0 GB (18,973,870,432 bytes, 17.7 GiB); lmstudio-community 16.8 GB; Unsloth UD-Q4_K_M 16.5-16.6 GB (Unsloth no longer lists a plain Q4_K_M; 'Nov 11 update' to Dynamic v3.1). Total memory at Q4_K_M is reported as about 17.6 GB at 8K context, 25.1 GB at 128K, 33.5 GB at 262K, so it fits in 61 GiB at any context. The vision projector is a separate file and is not fetched by default auto-match.",
   "weight": "minor",
   "where": "https://huggingface.co/bartowski/Qwen3.8-27B-GGUF ; https://huggingface.co/unsloth/Qwen3.8-27B-GGUF ; https://vramcalculator.com/qwen-3-8-27b-quantization/"
  },
  {
   "title": "llama.cpp b11669 was published 15 Oct 2026 and is new enough for Qwen3.8-27B",
   "detail": "Release page: 'released this 15 Oct 16:10', commit 620d222, note 'llama.cpp : bump version to 0.7.0', labelled Pre-release (year not displayed; a third-party issue dated 28 Oct 2026 confirms b11669 = v0.7.0 and b11960 = v0.8.0 published 2026-10-28). Latest today is b12317 (12 Nov). Qwen3.8-27B GGUFs carry general.architecture 'qwen35', reported registered 'since at least b10330' (August 2026); bartowski quantised with b10896; others ran it on b10760, b10909, b11062, b11377. All are older than b11669, so the bundled build should load it and already documents --spec-type draft-mtp. The exact minimum build is not verified from a primary llama.cpp source; neither bartowski's re-upload ('new tensor-layout', dated 11-09-2026, format ambiguous) nor Unsloth's 11 Nov update states a newer build requirement, but that is absence of a statement, not a test.",
   "weight": "important",
   "where": "https://github.com/ggml-org/llama.cpp/releases/tag/b11669 ; https://github.com/ogx-ai/ogx/issues/6836 ; https://scriptable.com/posts/llama-cpp/run-qwen3-8-27b-llama-cpp-macos/ ; https://huggingface.co/bartowski/Qwen3.8-27B-GGUF"
  },
  {
   "title": "b11669 will probably be too old for Qwen4-27B",
   "detail": "b11669 predates any Qwen 4 weights. Reports say Qwen 4 is trained on a new architecture, and the preview of that architecture (Qwen3.8-Flash-Next) needed a new llama.cpp architecture ('qwen4exp', PR #27742, reported merged 27 Aug 2026 by some guides and unmerged by others; not verified against GitHub). If Qwen4-27B ships with a new general.architecture string, an older build rejects the file at load. Inference, not fact, until the model card exists.",
   "weight": "important",
   "where": "https://www.yottalabs.ai/post/qwen-4-27b-release-date-specs-hardware-what-is-known-2026 ; https://unsloth.ai/docs/models/qwen3.8-next"
  },
  {
   "title": "Open RADV / Radeon 680M device-loss bug in the bundled build's range",
   "detail": "llama.cpp issue #27360 (opened 19 Aug 2026, still open, no maintainer fix): on RADV iGPUs the default '--load-mode auto' disables mmap and puts weights in Vulkan_Host (GTT) memory that --fit does not count, causing 'Not enough memory for command submission', 'vk::Queue::submit: ErrorDeviceLost' and kernel 'amdgpu_vm_validate() failed'. b10353 worked; b10470 onward fails; reproduced 26 Oct 2026 on a Ryzen 7 7735HS / Radeon 680M (Ubuntu 24.04, Mesa 25.2.8, b11889, GTT 14,403 MiB, 19 GiB model). Workarounds confirmed by reporters: '--load-mode mmap' (-lm mmap) or '--no-host'; both flags exist at b11669. Whether it bites depends on the GTT limit versus model plus host buffers; a large GTT may avoid it, but after a device loss later loads often fail until reboot.",
   "weight": "important",
   "where": "https://github.com/ggml-org/llama.cpp/issues/27360"
  },
  {
   "title": "Speed: expect roughly 2-4 tokens/s generation; no 680M 27B measurement exists",
   "detail": "No published 27B figure for the 680M or 7735HS was found. Nearest data: Radeon 890M iGPU 2.7 tok/s on Qwen3.8-27B (5.7 with MTP; backend and quant not stated); Strix Halo (far more memory bandwidth) dense 27B Q4_K_M CPU-only about 5.0 tok/s and 4.76-5.72 tok/s with partial Vulkan offload; llama.cpp Vulkan scoreboard 'AMD Ryzen 6000 Series' Llama 2 7B Q4_0 pp512 about 241 t/s, tg128 about 21 t/s; a search snippet (not opened) gives 15.42 t/s tg128 for a 7735HS/680M on RADV with the 7B. Scaling the 7B figures by file size (about 4.5x) gives 3.4-4.7 tok/s as an optimistic ceiling. Generation is 'bound by memory bandwidth, not compute'.",
   "weight": "important",
   "where": "https://vramcalculator.com/qwen3-8-27b-speed/ ; https://github.com/ggml-org/llama.cpp/issues/27360 ; https://github.com/ggml-org/llama.cpp/discussions/10879"
  },
  {
   "title": "Vulkan on the iGPU: likely helps prompt processing, little or no help for generation at this size",
   "detail": "On shared-memory APUs the GPU and CPU read the same DDR5, so generation speed is similar either way: the Strix Halo data shows Vulkan partial offload within about -5% to +14% of CPU-only for a dense 27B Q4_K_M. One ARM board report had Vulkan slower than CPU for a 32B Q4_K_M (different hardware). Vulkan's clear win on AMD iGPUs in the scoreboard is prompt processing on small models; whether that carries to 27B on the 680M is unverified. The model does run on RADV (RX 7900 XTX 48.5 tok/s via llama.cpp Vulkan). MTP speculative decoding is reported to roughly double decode on an 890M, unverified on the 680M. Only a local llama-bench with -ngl 0 versus full offload settles it.",
   "weight": "important",
   "where": "https://github.com/ggml-org/llama.cpp/issues/27360 ; https://forum.radxa.com/t/llama-cpp-benchmarks/27813 ; https://vramcalculator.com/qwen3-8-27b-speed/"
  },
  {
   "title": "'Q4' is best read as Q4_K_M; 4-bit holds up on this model",
   "detail": "bartowski's table marks Q4_K_M 'recommended': PPL 6.76 vs 6.744 base, mean KLD 0.0139, 95.0% same top-p. Q4_0 is measurably worse (KLD 0.0265, 92.8%) at 16.35 GB; Q4_K_S 16.36 GB (KLD 0.0156); IQ4_XS 15.48 GB (KLD 0.0188); Q5_K_M 20.92 GB (KLD 0.0053); Q6_K 23.86 GB (KLD 0.0030). Quesma (26 Aug 2026, Unsloth quants): 'if you go with a 4-bit quantization Q4_K_M (17GB), you won't notice a difference on these benchmarks' (GPQA Diamond, IFBench, Terminal-Bench 2.1). Since speed here is bandwidth-bound, larger quants cost speed about in proportion to size, so Q4_K_M is the sensible choice despite 61 GiB of memory.",
   "weight": "minor",
   "where": "https://huggingface.co/bartowski/Qwen3.8-27B-GGUF ; https://quesma.com/blog/qwen38-27b-quantizations-benchmarked/"
  },
  {
   "title": "Quality caveats at 4-bit",
   "detail": "Same-named Q4_K_M files differ: KLD 0.02094 (lmstudio-community, 16.8 GB), 0.01470 (ggml-org, 19.0 GB), 0.01126 (AtomicChat, 17.1 GB): 'a quant name tells you which recipe was requested, not what you are getting'. On an agentic score, 4-bit builds differ by about 10 points (Q4_K_XL 660, UD-Q4_K_M 652, IQ4_XS 650) against a 3-point noise floor. Turning reasoning effort down costs more than the quant does (about a 20-point swing off to max on BF16). No 4-bit-specific tool-calling or long-context tests were found, and KV-cache quantisation was not tested. Publishers replaced files after launch (Unsloth on 19 Aug and again 11 Nov; bartowski re-upload), so early downloads go stale.",
   "weight": "minor",
   "where": "https://vramcalculator.com/qwen-3-8-27b-quantization/ ; https://quesma.com/blog/qwen38-27b-quantizations-benchmarked/"
  }
 ],
 "recommendation": "Rehearse today with Qwen3.8-27B at Q4_K_M: it is the direct predecessor (same publisher, same 27B slot, Apache 2.0) and loads on the bundled llama.cpp b11669. Take bartowski/Qwen3.8-27B-GGUF Q4_K_M (17.44 GB) or ggml-org's (19.0 GB, lowest KLD of the plain Q4_K_M files measured); Unsloth's UD-Q4_K_M (16.6 GB) is the alternative. On first run: (1) run llama-bench with -ngl 0 and with full offload and keep whichever is faster; expect about 2-4 tokens/s generation, with Vulkan mainly helping prompt processing if at all; (2) if loading on Vulkan gives ErrorDeviceLost or 'Not enough memory for command submission', add --load-mode mmap or --no-host (known open bug on the 680M); (3) start with thinking off (--reasoning off or --chat-template-kwargs '{\"enable_thinking\":false}') or a small --reasoning-budget, because default xhigh thinking at this speed means tens of minutes per answer; use the model card's non-thinking sampling (temp 0.7, top_p 0.8, top_k 20, presence_penalty 1.5); (4) optionally try --spec-type draft-mtp, the one lever reported to roughly double decode on a similar iGPU.\n\nWhen Qwen 4.0 appears, watch for: the official repo Qwen/Qwen4-27B in the Qwen org (ignore placeholder and third-party 'Qwen4' repos until then); the licence (Apache 2.0 is precedent, not a promise; Flash-Next used a Qwen Community licence); the GGUF general.architecture string and the llama.cpp build number the quantiser states, compared with b11669 \u2014 expect to need a newer llama.cpp, since Qwen 4 is reported to use a new architecture; whether Vulkan supports all its operators (new architectures often land CPU/CUDA first); thinking defaults and template changes; and re-uploaded quants in the first weeks (wait for bartowski, Unsloth or ggml-org and re-download after their fixes). The Qwen4-Max preview ends 25 Nov 2026, which is the nearest date on which more news is plausible.",
 "not_checked": "Not verified: any Alibaba primary source for the 22 Sep Apsara lineup or for 'open weights' on the 27B (secondary write-ups only); the exact minimum llama.cpp build for Qwen3.8-27B (only 'at least b10330' from a guide, plus quantiser build b10896); the year on the b11669 release page (shown as '15 Oct', inferred 2026 from a dated third-party issue); the GitHub API route to llama.cpp was not available in this session, so release data came from the web page; the 15.42 t/s 7735HS/680M figure came from a search snippet, not the opened discussion page; no measured 27B tokens/s for the 680M or 7735HS exists in what I found, so the 2-4 tokens/s range is my inference from an 890M, Strix Halo and 7B scoreboard data; CPU-only DDR5 figures for this exact CPU; whether the RADV device-loss bug triggers with a 61 GiB shared-memory configuration; whether MTP works on Vulkan/RADV on the 680M; the meaning of bartowski's '11-09-2026' date and whether its new tensor layout was tested on b11669; the stealth-model/Qwen4 repo (HTTP 401); merge status of llama.cpp PR #27742; Debian 13's Mesa/RADV version was not looked up; current odds on the prediction market for Qwen 4 weights by 25 Nov."
}