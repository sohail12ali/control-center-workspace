//! What audio hardware does this machine actually have?
//!
//!     cargo run --example audio_probe --manifest-path desktop/src-tauri/Cargo.toml
//!
//! Written while building T-006 to answer a question the unit tests cannot:
//! whether `cpal` sees a real input device here, and at what format. That
//! matters because the recogniser and the voice-activity detector both need
//! 16 kHz mono — if the device already reports that, capture is a copy rather
//! than a resample.
//!
//! Kept rather than deleted because it is the first thing worth running when
//! someone reports that listening does not work: it separates "no microphone"
//! from "microphone fine, something later is broken", in one command, without
//! a build of the whole shell.

fn main() {
    use cpal::traits::{DeviceTrait, HostTrait};

    let host = cpal::default_host();
    println!("host: {}", host.id().name());

    match host.default_input_device() {
        Some(d) => {
            println!("input: {}", d.name().unwrap_or_default());
            match d.default_input_config() {
                Ok(c) => println!(
                    "  config: {} ch, {} Hz, {:?}{}",
                    c.channels(),
                    c.sample_rate().0,
                    c.sample_format(),
                    if c.sample_rate().0 == 16_000 && c.channels() == 1 {
                        "  <- already what speech recognition wants"
                    } else {
                        "  <- will be downmixed and resampled"
                    }
                ),
                Err(e) => println!("  config unreadable: {e}"),
            }
        }
        None => println!("input: NONE - nothing is set as the default input device"),
    }

    match host.default_output_device() {
        Some(d) => println!("output: {}", d.name().unwrap_or_default()),
        None => println!("output: NONE - spoken replies will have nowhere to go"),
    }
}
