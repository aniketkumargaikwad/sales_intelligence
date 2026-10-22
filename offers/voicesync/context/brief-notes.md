# What we already know about VoiceSync

Source: `docs/brief.md` (research date 2026-10-21), read 2026-10-22. VoiceSync's outbound engine
lives in the `calling-agent-2` repo, which is not connected to this project yet.

- **What it is:** an AI voice receptionist for Indian SMBs; the first segment is dental clinics in
  Maharashtra (brief §2).
- **Price, as the brief states it:** from ₹2,499/month, nothing upfront, 14-day pilot (brief §2).
- **Proof:** none we may claim yet; `proof` is empty in the brief's example (brief §2).
- **Strongest asset:** a personalised demo receptionist built for each prospect before contact
  (it already knows their timings), plus a `/for/<slug>` know-more page with view tracking and a
  callback form (brief §1.1). These stay in calling-agent-2 as the proof-asset adapter (brief §8).
- **What worked:** approval before anything leaves; fixed phone-first HTML email with LLM-filled
  slots only; honesty rules as lint; fit score orders everything; GitHub Actions cron (brief §1).
- **Data lessons:** free OpenStreetMap data had no contacts for Indian SMBs; Google Places needs
  billing enabled (brief §1.8).
- **Rules:** one business number for all human contact; never cold-call or cold-WhatsApp from it
  (TRAI rules, WhatsApp ban risk) (brief §1.12, §7).
- **Website:** https://voicesync.in could not be reached from the build environment on
  2026-10-22 (DNS lookup failed), so nothing here comes from the live site.
