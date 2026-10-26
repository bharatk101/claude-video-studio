import { Config } from "@remotion/cli/config";

// JPEG frames are fine for review sequences; renders to mp4 use the codec flags in the skill.
Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
