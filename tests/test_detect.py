"""Basic tests for the detect module."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from detect import (
    Detection,
    DetectionResult,
    check_ffmpeg,
    detect_from_upload,
    get_likely_species,
    get_species_filter,
    parse_species_name,
    week_of_year,
)

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"


# ── Unit tests ───────────────────────────────────────────────────


class TestParseSpeciesName:
    """Tests for species name parsing."""

    def test_standard_format(self) -> None:
        common, scientific = parse_species_name("Acridotheres tristis_Common Myna")
        assert common == "Common Myna"
        assert scientific == "Acridotheres tristis"

    def test_no_underscore(self) -> None:
        common, scientific = parse_species_name("Unknown Bird")
        assert common == "Unknown Bird"
        assert scientific == ""

    def test_multiple_underscores(self) -> None:
        common, scientific = parse_species_name("Genus species_Common_Name")
        assert common == "Common_Name"
        assert scientific == "Genus species"


class TestWeekOfYear:
    """Tests for week-of-year 48-week conversion."""

    def test_specific_dates(self) -> None:
        from datetime import date

        # Jan 1 -> Month 1, Week 1 -> Week 1
        assert week_of_year(date(2026, 1, 1)) == 1

        # Mid-year (June 15) -> Month 6, Week 3 -> (5*4) + 3 = 23
        assert week_of_year(date(2026, 6, 15)) == 23

        # Oct 8 -> Month 10, Week 2 -> (9*4) + 2 = 38
        assert week_of_year(date(2026, 10, 8)) == 38

        # Dec 31 -> Month 12, Week 4 -> (11*4) + 4 = 48
        assert week_of_year(date(2026, 12, 31)) == 48

    def test_all_days_of_year_in_bounds(self) -> None:
        from datetime import date, timedelta
        current = date(2026, 1, 1)
        end = date(2026, 12, 31)
        while current <= end:
            w = week_of_year(current)
            assert 1 <= w <= 48, f"Week {w} out of bounds for date {current}"
            current += timedelta(days=1)


class TestCheckFfmpeg:
    """Tests for ffmpeg detection."""

    def test_returns_bool(self) -> None:
        result = check_ffmpeg()
        assert isinstance(result, bool)


class TestGetLikelySpecies:
    """Tests for location-based species prediction."""

    def test_returns_list(self) -> None:
        result = get_likely_species(13.0, 77.6, week=41, top_n=5)
        assert isinstance(result, list)
        assert len(result) <= 5

    def test_tuple_format(self) -> None:
        result = get_likely_species(13.0, 77.6, week=41, top_n=3)
        if result:
            common, scientific, conf = result[0]
            assert isinstance(common, str)
            assert isinstance(scientific, str)
            assert isinstance(conf, float)
            assert 0.0 <= conf <= 1.0


class TestGetSpeciesFilter:
    """Tests for species filter set generation."""

    def test_returns_nonempty_set(self) -> None:
        species_set = get_species_filter(13.0, 77.6, week=38, min_confidence=0.01)
        assert isinstance(species_set, set)
        assert len(species_set) > 0

    def test_all_elements_are_strings(self) -> None:
        species_set = get_species_filter(13.0, 77.6, week=38, min_confidence=0.01)
        assert all(isinstance(s, str) for s in species_set)

    def test_low_threshold_includes_many_species(self) -> None:
        # Check that low-probability species are not excluded by a top 100 cap
        filter_001 = get_species_filter(13.0, 77.6, week=38, min_confidence=0.01)
        filter_003 = get_species_filter(13.0, 77.6, week=38, min_confidence=0.03)
        # 0.01 threshold should include at least as many or more species than 0.03 threshold
        assert len(filter_001) >= len(filter_003)
        assert len(filter_001) > 0



# ── Integration test (requires a sample audio file) ──────────────


@pytest.mark.skipif(
    not list(SAMPLES_DIR.glob("*.*")) if SAMPLES_DIR.exists() else True,
    reason="No sample audio files in samples/ directory",
)
class TestRunDetection:
    """Integration test that runs detection on real clips in samples/."""

    def test_real_clips_detection(self) -> None:
        """Run detection on real sample clips and verify output structure."""
        if not check_ffmpeg():
            pytest.skip("ffmpeg is required for processing non-WAV audio files")

        clips = list(SAMPLES_DIR.glob("*.mp3")) + list(SAMPLES_DIR.glob("*.wav"))
        if not clips:
            pytest.skip("No audio clips found in samples/")

        for sample in clips:
            result = detect_from_upload(sample, sample.name, min_confidence=0.1)

            assert isinstance(result, DetectionResult)
            assert result.error is None
            assert isinstance(result.detections, list)
            assert result.duration_s > 0.0

            # Verify each detection structure
            for det in result.detections:
                assert isinstance(det, Detection)
                assert isinstance(det.common_name, str)
                assert len(det.common_name) > 0
                assert isinstance(det.scientific_name, str)
                assert det.count >= 1
                assert 0.0 <= det.max_confidence <= 1.0
                assert det.first_heard_s >= 0.0
                assert ":" in det.first_heard_mmss
