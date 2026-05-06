use metricchrono_consensus::weighted_consensus;
use metricchrono_core::{MetricChronoError, Tier, geometric_ladder, ladder_values, tick_distance};

fn main() -> Result<(), MetricChronoError> {
    let tier = Tier::new(0.03, 0.05, 0.5, 1.0)?;
    let fine_tick = tick_distance(0.075, tier);

    let ladder = geometric_ladder(0.03, 0.05, 2.6, 6, 0.5, 1.0)?;
    let shock_ticks = ladder_values(1.62, &ladder)?;
    let source_a = [fine_tick, 0.0, 0.0, 0.0, 0.0, 0.0];
    let source_b = [fine_tick, fine_tick, 0.0, 0.0, 0.0, 0.0];
    let mut consensus = [0.0; 6];
    weighted_consensus(
        &[&source_a, shock_ticks.as_slice(), &source_b],
        &[0.34, 0.33, 0.33],
        &mut consensus,
    )?;

    println!(
        "# Public MetricChrono API smoke sample: fine_tick={fine_tick:.6}, shock_ticks={shock_ticks:?}, consensus={consensus:?}"
    );
    Ok(())
}
