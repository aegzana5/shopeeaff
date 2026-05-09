# Graph Report - .  (2026-05-09)

## Corpus Check
- 41 files · ~50,000 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 372 nodes · 602 edges · 28 communities (20 shown, 8 thin omitted)
- Extraction: 79% EXTRACTED · 21% INFERRED · 0% AMBIGUOUS · INFERRED: 124 edges (avg confidence: 0.82)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Viral Clip Formats|Viral Clip Formats]]
- [[_COMMUNITY_Claude AI Content Generation|Claude AI Content Generation]]
- [[_COMMUNITY_Caption & Script Generation|Caption & Script Generation]]
- [[_COMMUNITY_FFmpeg Video Pipeline|FFmpeg Video Pipeline]]
- [[_COMMUNITY_Bot Orchestration & Config|Bot Orchestration & Config]]
- [[_COMMUNITY_Outfit Matching|Outfit Matching]]
- [[_COMMUNITY_Video Render Core|Video Render Core]]
- [[_COMMUNITY_YouTube Upload|YouTube Upload]]
- [[_COMMUNITY_Instagram Playwright|Instagram Playwright]]
- [[_COMMUNITY_Image & Reel Creation|Image & Reel Creation]]
- [[_COMMUNITY_Trend Discovery|Trend Discovery]]
- [[_COMMUNITY_Trend Reshare & Affiliate|Trend Reshare & Affiliate]]
- [[_COMMUNITY_TikTok Tests|TikTok Tests]]
- [[_COMMUNITY_TikTok Upload|TikTok Upload]]
- [[_COMMUNITY_Viral Gen Tests|Viral Gen Tests]]
- [[_COMMUNITY_Text-to-Speech|Text-to-Speech]]
- [[_COMMUNITY_Stock Media|Stock Media]]
- [[_COMMUNITY_Scheduler & Cleanup|Scheduler & Cleanup]]
- [[_COMMUNITY_Instagram Setup|Instagram Setup]]
- [[_COMMUNITY_TikTok Setup|TikTok Setup]]
- [[_COMMUNITY_create_clip Alias|create_clip Alias]]
- [[_COMMUNITY_create_countdown_clip Alias|create_countdown_clip Alias]]
- [[_COMMUNITY_post_clip Alias|post_clip Alias]]

## God Nodes (most connected - your core abstractions)
1. `run_video_cycle` - 21 edges
2. `run_video_cycle()` - 20 edges
3. `run_post_cycle()` - 12 edges
4. `Config Module` - 12 edges
5. `post_short()` - 10 edges
6. `create_beat_hook_clip()` - 10 edges
7. `_make_fullbleed()` - 10 edges
8. `_build_ffmpeg_cmd()` - 10 edges
9. `create_price_reveal_clip()` - 10 edges
10. `create_clip()` - 10 edges

## Surprising Connections (you probably didn't know these)
- `generate_video_caption` --shares_data_with--> `Trend Signals Cache (JSON)`  [INFERRED]
  content_gen.py → assets/trend_signals.json
- `Stock Media Module (Pexels/Replicate)` --references--> `Replicate SDXL — Stable Diffusion Image Generation`  [INFERRED]
  stock_media.py → docs/superpowers/specs/2026-05-08-voiceover-visual-enrichment-design.md
- `Trend Reshare Module` --references--> `Instagram Session Cookies (JSON)`  [INFERRED]
  trend_reshare.py → assets/ig_session.json
- `run_video_cycle` --shares_data_with--> `Trend Signals Cache (JSON)`  [INFERRED]
  main.py → assets/trend_signals.json
- `run_trend_cycle` --shares_data_with--> `Trend Signals Cache (JSON)`  [INFERRED]
  main.py → assets/trend_signals.json

## Hyperedges (group relationships)
- **Video Production Pipeline** — viral_gen_module, video_gen_module, tts_module, stock_media_module, ffmpeg_bin [INFERRED 0.95]
- **Content Posting Pipeline (YouTube + Instagram)** — main_run_video_cycle, youtube_post_short, instagram_post_reel_clip, content_gen_generate_video_caption [EXTRACTED 1.00]
- **Trend-to-Affiliate Clip Pipeline** — main_run_trend_cycle, trend_discovery_discover_all, trend_reshare_find_shopee_match, trend_reshare_generate_affiliate_clip, trend_reshare_post_affiliate_clip [EXTRACTED 1.00]
- **Outfit Combo Generation Pipeline** — main_run_video_cycle, outfit_matcher_find_outfit_matches, image_ai_generate_model_image, viral_gen_create_outfit_clip, content_gen_generate_outfit_caption [EXTRACTED 1.00]
- **Shopee Data Layer** — shopee_module, shopee_get_trending_fashion, shopee_search_products, shopee_cache_json, shopee_affiliate_feed [EXTRACTED 1.00]
- **Claude API Consumers** — content_gen_generate_caption, content_gen_generate_video_caption, content_gen_generate_outfit_caption, content_gen_generate_reel_script, outfit_matcher_find_outfit_matches, trend_reshare_find_shopee_match [EXTRACTED 1.00]
- **Scheduled Jobs** — scheduler_module, main_run_post_cycle, main_run_video_cycle, main_run_trend_cycle [EXTRACTED 1.00]
- **Viral Clip Enrichment Pipeline — TTS + B-roll + FFmpeg** — tts_module, stock_media_module, viral_gen_module [EXTRACTED 0.95]
- **Trend Repost Affiliate Flow — Discovery + Matching + Clip Generation** — trend_discovery_module, trend_reshare_module, shopee_module [EXTRACTED 0.95]
- **Video Multi-Platform Upload — Render + TikTok + YouTube** — video_gen_module, tiktok_module, youtube_module [EXTRACTED 0.95]

## Communities (28 total, 8 thin omitted)

### Community 0 - "Viral Clip Formats"
Cohesion: 0.08
Nodes (39): API Separation Rationale — Three New Modules Keep API Concerns Separate from Rendering, create_beat_hook_clip() — Beat Hook Format, create_before_after_clip() — Before/After Format, create_clip() — Pillow+FFmpeg Video Render, create_post_image() — 1080x1080 Instagram Image, create_pov_meme_clip() — POV Meme Format, create_price_shock_clip() — Price Shock Format, ElevenLabs API — eleven_multilingual_v2 (+31 more)

### Community 1 - "Claude AI Content Generation"
Cohesion: 0.09
Nodes (43): Anthropic Claude API, generate_caption, generate_outfit_caption, generate_reel_script, generate_video_caption, ElevenLabs TTS API, fal.ai FLUX API, generate_model_image (+35 more)

### Community 2 - "Caption & Script Generation"
Cohesion: 0.08
Nodes (35): generate_caption(), generate_outfit_caption(), generate_reel_script(), generate_video_caption(), Generate outfit combination caption for all items., Generate short script/text overlays for 5-sec reel featuring multiple items., Generate bilingual Thai+EN caption with CTA and hashtags., Generate TikTok-native caption: scroll-stop hook + body + CTA + hashtags. (+27 more)

### Community 3 - "FFmpeg Video Pipeline"
Cohesion: 0.13
Nodes (34): generate_affiliate_clip(), _build_ffmpeg_cmd(), _composite_bg_frame(), create_countdown_clip(), create_price_reveal_clip(), _download_image(), _ffmpeg_bin(), _get_font() (+26 more)

### Community 4 - "Bot Orchestration & Config"
Cohesion: 0.08
Nodes (31): Playwright Browser State (JSON), Config Module, Content Generation Module, discover_all() — Aggregated Multi-Platform Discovery, discover_instagram() — instagrapi Account/Hashtag Scraper, discover_tiktok() — TikTokApi Scraper, extract_signals() — Hook/Hashtag/ClipType Extractor, Instagram Session Cookies (JSON) (+23 more)

### Community 5 - "Outfit Matching"
Cohesion: 0.11
Nodes (26): find_outfit_matches(), Find complementary Shopee products to complete an outfit. Uses Claude to determi, Return up to n complementary Shopee products for the given item., _fetch_and_parse(), get_trending_fashion(), _is_fashion(), _is_fresh(), _parse_feed() (+18 more)

### Community 6 - "Video Render Core"
Cohesion: 0.11
Nodes (21): create_clip(), _make_background(), Render 9s 1080x1920 MP4 — 3 products, 3 seconds each, Ken Burns zoom., Scale product image to fill 1080x1920, blur, darken., Render one frame with timed text overlays onto a copy of base_canvas., _render_frame(), FFmpeg cmd should include voiceover path when voiceover_path is given., create_clip with a bg_video_path that can't be opened falls back gracefully. (+13 more)

### Community 7 - "YouTube Upload"
Cohesion: 0.18
Nodes (13): _get_service(), post_short(), _prepare_yt_video(), YouTube Shorts upload via YouTube Data API v3. OAuth2 token stored at config.YOU, Return path to a version of the clip with only TTS audio (no background music)., Upload video as YouTube Short. Returns video ID., post_short returns video ID string on success., Title has #Shorts appended. (+5 more)

### Community 8 - "Instagram Playwright"
Cohesion: 0.22
Nodes (13): _build_browser_state(), _do_post(), _ensure_logged_in(), _FakeClient, get_client(), _make_context(), post_image(), post_reel() (+5 more)

### Community 9 - "Image & Reel Creation"
Cohesion: 0.23
Nodes (9): create_post_image(), create_reel(), _download_image(), _get_font(), Download product image, center-crop to 1080×1080, save as JPEG., Create 5-second MP4 reel from product images with text overlays., Output is clean product image — no brand strip artifacts at top., test_create_post_image_is_1080x1080() (+1 more)

### Community 10 - "Trend Discovery"
Cohesion: 0.33
Nodes (9): discover_all(), discover_instagram(), discover_tiktok(), _filter_posts(), test_discover_all_deduplicates_by_post_id(), test_discover_instagram_filters_below_threshold(), test_discover_instagram_returns_empty_on_login_failure(), test_discover_instagram_returns_filtered_posts() (+1 more)

### Community 11 - "Trend Reshare & Affiliate"
Cohesion: 0.29
Nodes (8): find_shopee_match(), _get_ig_client(), _reshare_instagram_story(), reshare_story(), test_find_shopee_match_returns_item_when_match_found(), test_find_shopee_match_returns_none_when_search_empty(), test_generate_affiliate_clip_picks_before_after_format(), test_reshare_story_returns_false_on_instagrapi_error()

### Community 12 - "TikTok Tests"
Cohesion: 0.22
Nodes (8): RuntimeError when session file does not exist., Returns list of cookies from valid JSON session file., RuntimeError with exact message when page.url contains 'login'., Returns 'posted' when the full upload flow succeeds., test_load_cookies_raises_if_no_session_file(), test_load_cookies_returns_list(), test_post_clip_raises_on_expired_session(), test_post_clip_returns_posted_on_success()

### Community 14 - "TikTok Upload"
Cohesion: 0.38
Nodes (6): _load_cookies(), post_clip(), TikTok clip upload via Playwright. Session loaded from assets/tiktok_session.jso, Update TikTok profile bio with affiliate link. Returns True on success., Upload clip to TikTok. Returns 'posted' on success., update_bio()

### Community 16 - "Viral Gen Tests"
Cohesion: 0.7
Nodes (4): _fake_img(), _make_ffmpeg_side_effect(), test_viral_clip_returns_mp4(), test_viral_clip_uses_voiceover_when_available()

## Knowledge Gaps
- **78 isolated node(s):** `Find complementary Shopee products to complete an outfit. Uses Claude to determi`, `Return up to n complementary Shopee products for the given item.`, `One-time setup: open a real browser, let user log into Instagram via Facebook, t`, `Download product image, center-crop to 1080×1080, save as JPEG.`, `Create 5-second MP4 reel from product images with text overlays.` (+73 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `run_video_cycle()` connect `Caption & Script Generation` to `Instagram Playwright`, `FFmpeg Video Pipeline`, `Outfit Matching`, `YouTube Upload`?**
  _High betweenness centrality (0.140) - this node is a cross-community bridge._
- **Why does `Config Module` connect `Bot Orchestration & Config` to `Viral Clip Formats`?**
  _High betweenness centrality (0.051) - this node is a cross-community bridge._
- **Why does `run_trend_cycle()` connect `Caption & Script Generation` to `FFmpeg Video Pipeline`, `Trend Discovery`, `Trend Reshare & Affiliate`?**
  _High betweenness centrality (0.049) - this node is a cross-community bridge._
- **Are the 16 inferred relationships involving `run_video_cycle()` (e.g. with `load_signals()` and `get_trending_fashion()`) actually correct?**
  _`run_video_cycle()` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `run_post_cycle()` (e.g. with `get_trending_fashion()` and `pick_top_items()`) actually correct?**
  _`run_post_cycle()` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `post_short()` (e.g. with `post_affiliate_clip()` and `run_video_cycle()`) actually correct?**
  _`post_short()` has 6 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Find complementary Shopee products to complete an outfit. Uses Claude to determi`, `Return up to n complementary Shopee products for the given item.`, `One-time setup: open a real browser, let user log into Instagram via Facebook, t` to the rest of the system?**
  _78 weakly-connected nodes found - possible documentation gaps or missing edges._