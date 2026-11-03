# Barriga Studio — fal.ai video cloud setup

## Goal
Use a **cloud video model** instead of Draw Things for video generation. This is an **isolated proof of integration** on a feature branch, not a working Studio UI integration or an automatic video pipeline.

## Provider and model
- fal.ai client: `fal-client` (Python SDK).
- Initial endpoint: `fal-ai/wan/v2.2-5b/image-to-video` (image reference + action prompt; up to ~5 seconds).
- Official API documentation: https://fal.ai/models/fal-ai/wan/v2.2-5b/image-to-video/api
- fal Python client: https://github.com/fal-ai/fal
- Official getting started requested: https://fal.ai/get-started.md (could not fetch from the assistant environment; verify directly when accessible).

## On the Mac
1. From `~/barriga-studio`, switch to `feat/fal-video-cloud-20261103` after fetching and reviewing the branch; do not overwrite uncommitted changes.
2. Install SDK in a virtual environment: `python3 -m venv .venv && source .venv/bin/activate && python -m pip install fal-client`.
3. Create an API key at https://fal.ai/dashboard/keys. Save it privately and put it in `FAL_KEY` in the server environment. Do not paste it into ChatGPT, a browser field, repository, or tracked file.
4. **Zero-charge dry run:** `python tools/fal_video.py --image-url "https://YOUR-IMAGE.jpg" --prompt "The animated character walks naturally" `.
5. Only **after explicit approval of spending**, run with `--execute`. This invokes a chargeable model.
6. Verify that the result prints a real HTTPS video URL and plays a genuine moving clip. The tool prints the URL; it does not yet download MP4 into the app.

## Security and limits
- Maximum project budget previously discussed: US$50/month. This script does **not** implement provider-side budget enforcement; the operator must set/manage spending controls at fal and explicitly approve each execution.
- Never call fal directly from `index.html` or browser JS with `FAL_KEY`; authentication must remain on a server.
- The current script does not implement auth, requests queue persistence, studio UI wiring, job recovery, voice, multi-scene continuity, saved MP4, or automatic retries.
- URLs of uploaded images are transferred to the provider; use approved reference images.
- No generation has been run, no API key has been configured, and no charges have been incurred by adding these files.

## Acceptance criteria for the next phase
A test image must generate a five-second video with genuine temporal motion and a retrievable MP4, and the request ID/result must later be persisted privately. Next: implement an authenticated local backend adapter and integrate the Studio button after acceptance.
