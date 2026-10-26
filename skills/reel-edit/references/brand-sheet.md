# The brand sheet

This skill holds the editing workflow and preferences. The creator's look
(colours, fonts, caption style, hook style, recurring motifs) lives outside
it, in the project's brand sheet, so the skill works for any creator.

## Where it lives

`brand/BRAND.md` at the project root, with any theme code next to it
(`brand/*.tsx`). Read it at the start of every own-channel video, before
proposing graphics or captions. Copy the code a video needs into
`src/shared/` (or the video's folder) the first time it is used.

Brand deals are the exception: they use the partner's palette and logo, from
that campaign's own notes.

## No brand sheet yet

Do not borrow another creator's look and do not invent one silently. Ask the
creator to set one up, offering to pull it from what they already have:

1. **Their website or existing videos**: read the site's CSS (colour tokens,
   fonts) or sample frames from a past video they like.
2. **Colour**: a ground (paper, dark, white), one main colour for headlines
   and shapes, one accent, and which colours never go over video.
3. **Type**: a headline face (and italic or accent face), a label or UI face,
   the caption face and weight.
4. **Captions**: which treatment is the default (outlined TikTok style, plain
   white, an emphasis-word option), and where the line sits on their framing.
5. **Hooks and titles**: the default hook style and any options.
6. **Motifs**: grounds, cards, label style, transitions they want repeated so
   every video feels like one channel.
7. **Music**: beds they like, where their sound pack lives.

Write the answers into `brand/BRAND.md` using the sections above, show a few
sample frames, and get a yes before the first video uses it.

Until a sheet exists, neutral defaults keep the edit moving: white Inter 800
captions with a black outline (`components/Caption.tsx`), headline type in a
clean sans, and graphics on a plain dark or light ground.

## Options, not rules

A brand sheet can list several caption treatments, hook styles or palettes.
Treat anything marked as an option as available, not required; use the
sheet's main theme unless the creator picks an option for a video.
