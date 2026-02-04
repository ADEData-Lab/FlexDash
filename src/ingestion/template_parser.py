"""
Template Parser for V1.2 Excel data templates and custom formats.

Handles standardised ADE Data Template V1.2 format as well as
custom submissions from various contributors.
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ParsedData:
    """Container for parsed data from a single submission."""
    contributor_id: str
    contributor_name: str
    submission_date: datetime
    template_version: str
    sector: str  # 'domestic', 'ic', or 'mixed'

    # Core data
    assets: pd.DataFrame = field(default_factory=pd.DataFrame)
    events: pd.DataFrame = field(default_factory=pd.DataFrame)
    services: pd.DataFrame = field(default_factory=pd.DataFrame)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    parse_warnings: List[str] = field(default_factory=list)
    parse_errors: List[str] = field(default_factory=list)


class TemplateParser:
    """
    Parser for ADE Flexibility Dashboard data templates.

    Supports V1.2 standard format and custom formats from various contributors.
    """

    def __init__(self, taxonomy: Dict = None):
        """
        Initialize parser with optional taxonomy for field mapping.

        Args:
            taxonomy: Asset and service taxonomy for standardization
        """
        self.taxonomy = taxonomy or {}
        self._contributor_counter = 0

    def parse_file(self, filepath: Path) -> ParsedData:
        """
        Parse a single Excel file and return structured data.

        Args:
            filepath: Path to the Excel file

        Returns:
            ParsedData object with extracted information
        """
        filepath = Path(filepath)
        logger.info(f"Parsing file: {filepath.name}")

        # Generate pseudonymous ID
        self._contributor_counter += 1
        contributor_id = f"CONTRIB_{self._contributor_counter:03d}"

        filename = filepath.name.lower()


        # Route to parsers using content-based detection.
        # Filenames are not reliable and may contain sensitive identifiers.

        # Industry summary table (simple 3-column layout).
        try:
            head = pd.read_excel(filepath, sheet_name=0, nrows=1)
            cols = {str(c).strip().lower() for c in head.columns}
            if {"industry", "mws", "sites"}.issubset(cols):
                return self._parse_industry_summary_table(filepath, contributor_id)
        except Exception:
            pass

        # ADE template V1.2 (structure detection).
        try:
            preview = pd.read_excel(filepath, sheet_name=0, header=None, nrows=60)
            preview_text = " ".join(
                " ".join(str(v) for v in preview.iloc[i].values if pd.notna(v)).strip().lower()
                for i in range(min(len(preview), 60))
            )
            looks_like_template = (
                "part 2 - managed assets" in preview_text
                and "no. in portfolio" in preview_text
            )
            if looks_like_template:
                contributor_name = None
                try:
                    # Extract company name from Part 1 (best-effort).
                    for r in range(min(len(preview), 30)):
                        for c in range(preview.shape[1]):
                            v = preview.iat[r, c]
                            if isinstance(v, str) and v.strip().lower() == "company name":
                                for rr in range(r + 1, min(r + 15, len(preview))):
                                    for cc in [c - 1, c, c + 1]:
                                        if 0 <= cc < preview.shape[1]:
                                            vv = preview.iat[rr, cc]
                                            if isinstance(vv, str) and vv.strip():
                                                contributor_name = vv.strip()
                                                break
                                    if contributor_name:
                                        break
                                break
                        if contributor_name:
                            break
                except Exception:
                    contributor_name = None

                name = contributor_name or filepath.stem
                logger.info(f"Detected ADE template structure in {filepath.name}; parsing as V1.2")
                return self._parse_template_v1_2(filepath, contributor_id, name)
        except Exception:
            pass

        # Non-template TOU / implicit-flex return (fallback).
        if self._looks_like_non_template_tou_return(filepath):
            return self._parse_non_template_tou_raw(filepath, contributor_id)

        return self._parse_generic(filepath, contributor_id)

    def _looks_like_non_template_tou_return(self, filepath: Path) -> bool:
        'Heuristic check for a non-template TOU/implicit-flex spreadsheet.'
        try:
            df = pd.read_excel(filepath, sheet_name=0, nrows=3)
            cols = [str(c).strip().lower() for c in df.columns]
            return (
                "assets" in cols
                and "description" in cols
                and any("1st nov 2024" in c for c in cols)
            )
        except Exception:
            return False


    def _parse_non_template_tou_raw(self, filepath: Path, contributor_id: str) -> ParsedData:
        """Parse non-template TOU/implicit-flex return format (fallback)."""
        logger.info("Using non-template TOU fallback parser")

        df = pd.read_excel(filepath, sheet_name=0, header=0)
        warnings: List[str] = []

        # The non-template TOU return contains two blocks:
        #   1) Asset counts at specific dates (incl. 7 Dec 2025 "Current" - outside Phase 1)
        #   2) Import/Export (MWh) rows that don't map cleanly to the V1.2 template.
        #
        # For Phase 1 (Nov 2024-Feb 2025), we ingest counts only from the first block and do NOT
        # infer MW capacity from counts (the template separately requests deduplicated/coincident
        # MW in section 3.2).

        cols = list(df.columns)
        if len(cols) < 5:
            return ParsedData(
                contributor_id=contributor_id,
                contributor_name=filepath.stem,
                submission_date=datetime.now(),
                template_version="Custom",
                sector="mixed",
                assets=pd.DataFrame(),
                events=pd.DataFrame(),
                services=pd.DataFrame(),
                metadata={'format': 'tou_non_template_raw', 'capacity_source': 'missing_3.2'},
                parse_warnings=["Non-template TOU return structure unexpected; could not parse asset counts block"],
                parse_errors=[]
            )

        # Identify the Feb 2025 column (often comes through as a datetime)
        feb_col = None
        for c in cols:
            if hasattr(c, "year") and getattr(c, "year", None) == 2025 and getattr(c, "month", None) == 2:
                feb_col = c
                break
        if feb_col is None:
            feb_col = cols[4]

        df = df.rename(
            columns={
                cols[0]: "sector",
                cols[1]: "asset_type",
                cols[3]: "count_nov_2024",
                feb_col: "count_feb_2025",
            }
        )

        # Trim to the first block (stop when the "Assets" header reappears for Import/Export)
        block_rows = []
        for _, row in df.iterrows():
            asset_type = row.get("asset_type")
            if pd.notna(asset_type) and str(asset_type).strip().lower() == "assets":
                # The second block starts with "Assets" + Import/Export labels
                if "import" in str(row.get(cols[2], "")).lower():
                    break
            block_rows.append(row)
        df_block = pd.DataFrame(block_rows)

        df_block = df_block.dropna(subset=["asset_type"])
        df_block["sector"] = df_block["sector"].ffill()

        assets: List[Dict[str, Any]] = []
        for _, row in df_block.iterrows():
            asset_type = row.get("asset_type")
            if pd.isna(asset_type) or str(asset_type).strip().lower() == "assets":
                continue

            asset_class = self._map_asset_type(str(asset_type))
            sector_raw = str(row.get("sector", "")).strip().lower()
            sector = "domestic" if "domestic" in sector_raw else "ic"

            count_val = row.get("count_feb_2025", 0)
            try:
                count = int(float(count_val)) if pd.notna(count_val) else 0
            except (ValueError, TypeError):
                count = 0

            if count > 0:
                assets.append(
                    {
                        "asset_class": asset_class,
                        "sector": sector,
                        "count": count,
                        "portfolio_count": count,
                        "count_basis": "as_of_2025-02-28",
                        "capacity_mw": None,
                        "capacity_basis": "missing_3.2",
                    }
                )

        if assets:
            warnings.append(
                "Non-template TOU return provided asset counts only; MW capacity (template section 3.2) not provided; capacity omitted"
            )
        assets_df = pd.DataFrame(assets) if assets else pd.DataFrame()

        return ParsedData(
            contributor_id=contributor_id,
            contributor_name=filepath.stem,
            submission_date=datetime.now(),
            template_version="Custom",
            sector="mixed",
            assets=assets_df,
            events=pd.DataFrame(),
            services=pd.DataFrame(),
            metadata={'format': 'tou_non_template_raw', 'capacity_source': 'missing_3.2'},
            parse_warnings=warnings,
            parse_errors=[]
        )

    def _parse_industry_summary_table(self, filepath: Path, contributor_id: str) -> ParsedData:
        """Parse industry summary table format (columns: Industry, MWs, Sites)."""
        logger.info("Using industry summary parser")

        df = pd.read_excel(filepath, sheet_name=0, header=0)

        # Columns: Industry, MWs, Sites
        df.columns = ['industry', 'capacity_mw', 'site_count']
        df = df.dropna(subset=['industry'])

        # Create standardized asset records
        assets = []
        for _, row in df.iterrows():
            if pd.notna(row['industry']) and row['industry'] != 'Industry':
                assets.append({
                    'asset_class': self._map_industry_to_asset(str(row['industry'])),
                    'sector': 'ic',
                    'count': int(row.get('site_count', 1)) if pd.notna(row.get('site_count')) else 1,
                    'capacity_mw': float(row.get('capacity_mw', 0)) if pd.notna(row.get('capacity_mw')) else 0
                })

        assets_df = pd.DataFrame(assets) if assets else pd.DataFrame()

        return ParsedData(
            contributor_id=contributor_id,
            contributor_name=filepath.stem,
            submission_date=datetime.now(),
            template_version="Custom",
            sector="ic",
            assets=assets_df,
            events=pd.DataFrame(),
            services=pd.DataFrame(),
            metadata={'format': 'industry_summary'},
            parse_warnings=[],
            parse_errors=[]
        )

    def _parse_template_v1_2(self, filepath: Path, contributor_id: str, contributor_name: str) -> ParsedData:
        """
        Parse the ADE Data Template V1.2 format.

        Extracts (where present):
          - Part 2: managed asset counts + market share + winter-active counts
          - Part 3.1: explicit flexibility energy (MWh) available/delivered, turn-up/turn-down
          - Part 3.2: explicit flexibility capacity (MW) available/delivered, turn-up/turn-down

        Important: We do NOT infer MW capacity from device/site counts. The template separately requests
        a deduplicated/coincident MW figure in Part 3.2; if missing, capacity is treated as missing.
        """
        logger.info(f'Using ADE Template V1.2 parser for {contributor_name}')

        warnings: List[str] = []
        errors: List[str] = []

        try:
            df = pd.read_excel(filepath, sheet_name=0, header=None)
        except Exception as e:
            return ParsedData(
                contributor_id=contributor_id,
                contributor_name=contributor_name,
                submission_date=datetime.now(),
                template_version='V1.2',
                sector='unknown',
                assets=pd.DataFrame(),
                events=pd.DataFrame(),
                services=pd.DataFrame(),
                metadata={'format': 'ade_template_v1.2', 'capacity_source': 'missing_3.2'},
                parse_warnings=[],
                parse_errors=[f'Failed to read Excel: {e}']
            )

        def row_text(i: int) -> str:
            row = df.iloc[i]
            return ' '.join(str(v) for v in row.values if pd.notna(v)).strip().lower()

        def find_row_contains_all(*needles: str) -> Optional[int]:
            needles_l = [n.lower() for n in needles]
            for i in range(len(df)):
                t = row_text(i)
                if all(n in t for n in needles_l):
                    return i
            return None

        def normalise_sector(s: Any) -> Optional[str]:
            if s is None or (isinstance(s, float) and pd.isna(s)):
                return None
            txt = str(s).strip().lower()
            if 'domestic' in txt:
                return 'domestic'
            if 'i&c' in txt or 'i & c' in txt or txt == 'ic' or 'industrial' in txt:
                return 'ic'
            return None

        def parse_float(val: Any) -> Optional[float]:
            if val is None or (isinstance(val, float) and pd.isna(val)):
                return None
            if isinstance(val, (int, float)) and not pd.isna(val):
                return float(val)
            s = str(val).strip().replace(',', '').replace('\xa0', '').strip()
            if not s:
                return None
            is_lt = s.startswith('<')
            if is_lt:
                s = s[1:].strip()
            m = re.search(r'(-?\d+(?:\.\d+)?)', s)
            if not m:
                return None
            num = float(m.group(1))
            if is_lt:
                return num / 2.0
            return num

        def parse_int_count(val: Any) -> Optional[int]:
            if val is None or (isinstance(val, float) and pd.isna(val)):
                return None
            if isinstance(val, (int, float)) and not pd.isna(val):
                try:
                    return int(float(val))
                except Exception:
                    return None
            s = str(val).strip().lower().replace(',', '')
            if not s:
                return None
            if 'mw' in s or 'kw' in s:
                return None
            m = re.search(r'(\d+)', s)
            if not m:
                return None
            try:
                return int(m.group(1))
            except Exception:
                return None

        # --- Part 2: managed assets table
        part2_header = find_row_contains_all('assets', 'no. in portfolio')
        part2: Dict[tuple[str, str], Dict[str, Any]] = {}
        if part2_header is None:
            warnings.append('Template V1.2: could not locate Part 2 header row (assets / portfolio counts)')
        else:
            header_row = df.iloc[part2_header].tolist()
            try:
                assets_col = next(i for i, v in enumerate(header_row) if str(v).strip().lower() == 'assets')
            except StopIteration:
                assets_col = 12

            sector_col = assets_col
            asset_label_col = assets_col + 1

            def col_idx(label: str, default: int) -> int:
                for i, v in enumerate(header_row):
                    if str(v).strip().lower() == label.lower():
                        return i
                return default

            portfolio_col = col_idx('No. in portfolio', assets_col + 3)
            market_share_col = col_idx('Market share (%)', assets_col + 4)
            winter_col = col_idx('No. used in winter 2024-25', assets_col + 5)
            remarks_col = col_idx('Remarks', assets_col + 6)

            current_sector: Optional[str] = None
            for i in range(part2_header + 1, min(part2_header + 60, len(df))):
                t = row_text(i)
                if '3.1' in t or '3.2' in t or 'part 3' in t:
                    break

                sec = normalise_sector(df.iat[i, sector_col] if sector_col < df.shape[1] else None)
                if sec:
                    current_sector = sec

                asset_label = df.iat[i, asset_label_col] if asset_label_col < df.shape[1] else None
                if current_sector is None or asset_label is None or (isinstance(asset_label, float) and pd.isna(asset_label)):
                    continue

                asset_class = self._map_asset_type(str(asset_label))

                portfolio = parse_int_count(df.iat[i, portfolio_col] if portfolio_col < df.shape[1] else None)
                market_share = parse_float(df.iat[i, market_share_col] if market_share_col < df.shape[1] else None)
                winter_active = parse_int_count(df.iat[i, winter_col] if winter_col < df.shape[1] else None)

                remarks = df.iat[i, remarks_col] if remarks_col < df.shape[1] else None
                remarks_str = (
                    str(remarks).strip()
                    if remarks is not None and not (isinstance(remarks, float) and pd.isna(remarks))
                    else None
                )

                count = winter_active if winter_active is not None else portfolio
                count_basis = 'winter_active' if winter_active is not None else 'portfolio'

                part2[(current_sector, asset_class)] = {
                    'portfolio_count': portfolio,
                    'market_share_pct': market_share,
                    'winter_active_count': winter_active,
                    'remarks': remarks_str,
                    'count': count,
                    'count_basis': count_basis,
                }

        # --- Part 3.1 / 3.2 tables
        def find_section_header(section_label: str) -> Optional[int]:
            start = find_row_contains_all(section_label)
            if start is None:
                return None
            for j in range(start, min(start + 8, len(df))):
                row = df.iloc[j].tolist()
                if any(str(v).strip().lower() == 'assets' for v in row if pd.notna(v)):
                    if 'available' in row_text(j) and 'delivered' in row_text(j):
                        return j
            return None

        def parse_directional_table(header_idx: int) -> Dict[tuple[str, str], Dict[str, Any]]:
            row = df.iloc[header_idx].tolist()
            try:
                assets_col = next(i for i, v in enumerate(row) if str(v).strip().lower() == 'assets')
            except StopIteration:
                assets_col = 1

            def col_find(label: str, default: int) -> int:
                for i, v in enumerate(row):
                    if str(v).strip().lower() == label.lower():
                        return i
                return default

            avail_up_col = col_find('Available (Turn up)', assets_col + 5)
            avail_down_col = col_find('Available (Turn down)', assets_col + 6)
            deliv_up_col = col_find('Delivered (Turn up)', assets_col + 7)
            deliv_down_col = col_find('Delivered (Turn down)', assets_col + 8)

            sector_col = assets_col
            asset_label_col = assets_col + 1

            current_sector: Optional[str] = None
            out: Dict[tuple[str, str], Dict[str, Any]] = {}

            for i in range(header_idx + 1, min(header_idx + 40, len(df))):
                t = row_text(i)
                if 'part 4' in t:
                    break
                # Stop on the next numbered section marker (e.g. 3.2) to avoid consuming explanatory rows.
                if t.startswith('3.2') or t.startswith('3.3'):
                    break
                # Stop if we hit the next section header (another "Assets" header row).
                # This prevents section 3.1 parsing from accidentally consuming section 3.2 rows.
                row_i = df.iloc[i].tolist()
                if any(str(v).strip().lower() == 'assets' for v in row_i if pd.notna(v)):
                    if 'available' in t and 'delivered' in t:
                        break

                sec = normalise_sector(df.iat[i, sector_col] if sector_col < df.shape[1] else None)
                if sec:
                    current_sector = sec

                asset_label = df.iat[i, asset_label_col] if asset_label_col < df.shape[1] else None
                if current_sector is None or asset_label is None or (isinstance(asset_label, float) and pd.isna(asset_label)):
                    continue

                asset_class = self._map_asset_type(str(asset_label))
                av_up = parse_float(df.iat[i, avail_up_col] if avail_up_col < df.shape[1] else None)
                av_down = parse_float(df.iat[i, avail_down_col] if avail_down_col < df.shape[1] else None)
                dl_up = parse_float(df.iat[i, deliv_up_col] if deliv_up_col < df.shape[1] else None)
                dl_down = parse_float(df.iat[i, deliv_down_col] if deliv_down_col < df.shape[1] else None)

                # Skip completely empty rows (all values missing or zero)
                if not any(v for v in [av_up, av_down, dl_up, dl_down] if v not in (None, 0, 0.0)):
                    continue

                out[(current_sector, asset_class)] = {
                    'available_turn_up': av_up or 0.0,
                    'available_turn_down': av_down or 0.0,
                    'delivered_turn_up': dl_up or 0.0,
                    'delivered_turn_down': dl_down or 0.0,
                }

            return out

        p31_header = find_section_header('3.1')
        p31 = parse_directional_table(p31_header) if p31_header is not None else {}
        if p31_header is None:
            warnings.append('Template V1.2: section 3.1 (MWh) not found or not populated')

        p32_header = find_section_header('3.2')
        p32 = parse_directional_table(p32_header) if p32_header is not None else {}
        if p32_header is None:
            warnings.append('Template V1.2: section 3.2 (MW) not found or not populated')

        # Merge keys across parts
        keys = set(part2.keys()) | set(p31.keys()) | set(p32.keys())
        rows: List[Dict[str, Any]] = []
        for (sector, asset_class) in sorted(keys):
            r: Dict[str, Any] = {'sector': sector, 'asset_class': asset_class}
            r.update(part2.get((sector, asset_class), {}))

            if (sector, asset_class) in p31:
                r.update(
                    {
                        'available_turn_up_mwh': p31[(sector, asset_class)]['available_turn_up'],
                        'available_turn_down_mwh': p31[(sector, asset_class)]['available_turn_down'],
                        'delivered_turn_up_mwh': p31[(sector, asset_class)]['delivered_turn_up'],
                        'delivered_turn_down_mwh': p31[(sector, asset_class)]['delivered_turn_down'],
                    }
                )

            if (sector, asset_class) in p32:
                r.update(
                    {
                        'available_turn_up_mw': p32[(sector, asset_class)]['available_turn_up'],
                        'available_turn_down_mw': p32[(sector, asset_class)]['available_turn_down'],
                        'delivered_turn_up_mw': p32[(sector, asset_class)]['delivered_turn_up'],
                        'delivered_turn_down_mw': p32[(sector, asset_class)]['delivered_turn_down'],
                    }
                )
                # Conservative single-value capacity for current dashboard totals.
                r['capacity_mw'] = max(r.get('available_turn_up_mw') or 0.0, r.get('available_turn_down_mw') or 0.0)
                r['capacity_basis'] = 'max_available_turn_up_down'
            else:
                r['capacity_mw'] = None
                r['capacity_basis'] = 'missing_3.2'

            if 'count' not in r:
                r['count'] = None

            rows.append(r)

        assets_df = pd.DataFrame(rows) if rows else pd.DataFrame()

        # --- Part 4: unmanaged ToU tariffs (suppliers)
        # This section is optional and only applies to suppliers; we keep it separate from asset-level records.
        def find_tou_header(must_contain: List[str]) -> Optional[int]:
            for i in range(len(df)):
                t = row_text(i)
                if all(x.lower() in t for x in must_contain):
                    return i
            return None

        def parse_tou_table_41(header_idx: int) -> pd.DataFrame:
            header = df.iloc[header_idx].tolist()

            def col_contains(substr: str, default: int) -> int:
                for j, v in enumerate(header):
                    if substr.lower() in str(v).strip().lower():
                        return j
                return default

            tariff_col = col_contains("tariff name", 1)
            sector_tgt_col = col_contains("target a specific sector", 6)
            asset_tgt_col = col_contains("target specific asset", 8)
            static_dyn_col = col_contains("static/dynamic", 11)
            peak_col = col_contains("peak times", 14)
            offpeak_col = col_contains("off-peak times", 15)
            customers_col = col_contains("unmanaged customers", 17)

            rows_out: List[Dict[str, Any]] = []
            for i in range(header_idx + 1, min(header_idx + 60, len(df))):
                t_row = row_text(i)
                if t_row.startswith("4.2") or t_row.startswith("4.3") or t_row.startswith("part 5"):
                    break
                name = df.iat[i, tariff_col] if tariff_col < df.shape[1] else None
                if name is None or (isinstance(name, float) and pd.isna(name)):
                    continue
                if isinstance(name, (int, float)) and float(name) == 0:
                    continue
                name_s = str(name).strip()
                if not name_s:
                    continue
                if name_s.lower().startswith("example"):
                    continue

                sector_tgt = df.iat[i, sector_tgt_col] if sector_tgt_col < df.shape[1] else None
                asset_tgt = df.iat[i, asset_tgt_col] if asset_tgt_col < df.shape[1] else None
                tariff_type = df.iat[i, static_dyn_col] if static_dyn_col < df.shape[1] else None
                peak = df.iat[i, peak_col] if peak_col < df.shape[1] else None
                offpeak = df.iat[i, offpeak_col] if offpeak_col < df.shape[1] else None
                customers = df.iat[i, customers_col] if customers_col < df.shape[1] else None

                rows_out.append(
                    {
                        "tariff_name": name_s,
                        "target_sector": str(sector_tgt).strip() if sector_tgt is not None and not (isinstance(sector_tgt, float) and pd.isna(sector_tgt)) else None,
                        "target_asset": str(asset_tgt).strip() if asset_tgt is not None and not (isinstance(asset_tgt, float) and pd.isna(asset_tgt)) else None,
                        "tariff_type": str(tariff_type).strip() if tariff_type is not None and not (isinstance(tariff_type, float) and pd.isna(tariff_type)) else None,
                        "peak_times": str(peak).strip() if peak is not None and not (isinstance(peak, float) and pd.isna(peak)) else None,
                        "offpeak_times": str(offpeak).strip() if offpeak is not None and not (isinstance(offpeak, float) and pd.isna(offpeak)) else None,
                        "unmanaged_customers": parse_int_count(customers),
                    }
                )

            return pd.DataFrame(rows_out) if rows_out else pd.DataFrame()

        def parse_tou_table_42(header_idx: int) -> pd.DataFrame:
            header = df.iloc[header_idx].tolist()

            def col_contains(substr: str, default: int) -> int:
                for j, v in enumerate(header):
                    if substr.lower() in str(v).strip().lower():
                        return j
                return default

            tariff_col = col_contains("tariff name", 1)
            td_col = col_contains("turn-down", 6)
            tu_col = col_contains("turn-up", 8)

            rows_out: List[Dict[str, Any]] = []
            for i in range(header_idx + 1, min(header_idx + 80, len(df))):
                t_row = row_text(i)
                if t_row.startswith("4.3") or t_row.startswith("part 5"):
                    break
                name = df.iat[i, tariff_col] if tariff_col < df.shape[1] else None
                if name is None or (isinstance(name, float) and pd.isna(name)):
                    continue
                if isinstance(name, (int, float)) and float(name) == 0:
                    continue
                name_s = str(name).strip()
                if not name_s or name_s.lower().startswith("example"):
                    continue

                td = parse_float(df.iat[i, td_col] if td_col < df.shape[1] else None)
                tu = parse_float(df.iat[i, tu_col] if tu_col < df.shape[1] else None)
                if td is None and tu is None:
                    continue
                rows_out.append(
                    {
                        "tariff_name": name_s,
                        "total_turn_down_mwh": td,
                        "total_turn_up_mwh": tu,
                    }
                )

            return pd.DataFrame(rows_out) if rows_out else pd.DataFrame()

        def parse_tou_table_43(header_idx: int) -> pd.DataFrame:
            header = df.iloc[header_idx].tolist()

            def col_contains(substr: str, default: int) -> int:
                for j, v in enumerate(header):
                    if substr.lower() in str(v).strip().lower():
                        return j
                return default

            def col_all(substrings: List[str], default: int) -> int:
                subs = [s.lower() for s in substrings]
                for j, v in enumerate(header):
                    t = str(v).strip().lower()
                    if all(s in t for s in subs):
                        return j
                return default

            tariff_col = col_contains("tariff name", 1)
            mwh_td_col = col_all(["mwh", "turn down"], 6)
            mwh_tu_col = col_all(["mwh", "turn up"], 8)
            mw_td_col = col_all(["capacity", "turn down"], 11)
            mw_tu_col = col_all(["capacity", "turn up"], 14)

            rows_out: List[Dict[str, Any]] = []
            for i in range(header_idx + 1, min(header_idx + 80, len(df))):
                t_row = row_text(i)
                if t_row.startswith("part 5"):
                    break
                name = df.iat[i, tariff_col] if tariff_col < df.shape[1] else None
                if name is None or (isinstance(name, float) and pd.isna(name)):
                    continue
                if isinstance(name, (int, float)) and float(name) == 0:
                    continue
                name_s = str(name).strip()
                if not name_s or name_s.lower().startswith("example"):
                    continue

                td_mwh = parse_float(df.iat[i, mwh_td_col] if mwh_td_col < df.shape[1] else None)
                tu_mwh = parse_float(df.iat[i, mwh_tu_col] if mwh_tu_col < df.shape[1] else None)
                td_mw = parse_float(df.iat[i, mw_td_col] if mw_td_col < df.shape[1] else None)
                tu_mw = parse_float(df.iat[i, mw_tu_col] if mw_tu_col < df.shape[1] else None)
                # Many template workbooks include placeholder zeros in the Part 4.3 MW columns.
                # Treat rows with no provided MWh values and only 0 MW placeholders as "missing"
                # so we don't accidentally (a) count a contributor as providing implicit MW or
                # (b) publish misleading zeros in admin QA outputs.
                if (td_mwh is None and tu_mwh is None) and (
                    (td_mw is None or td_mw == 0.0) and (tu_mw is None or tu_mw == 0.0)
                ):
                    continue

                rows_out.append(
                    {
                        "tariff_name": name_s,
                        "busiest_hh_turn_down_mwh": td_mwh,
                        "busiest_hh_turn_up_mwh": tu_mwh,
                        "busiest_hh_turn_down_mw": td_mw,
                        "busiest_hh_turn_up_mw": tu_mw,
                        "capacity_mw": max(td_mw or 0.0, tu_mw or 0.0) if (td_mw is not None or tu_mw is not None) else None,
                        "capacity_basis": "tou_busiest_hh",
                    }
                )

            return pd.DataFrame(rows_out) if rows_out else pd.DataFrame()

        tou_41_header = find_tou_header(["tariff name", "unmanaged customers"])
        tou_42_header = find_tou_header(["tariff name", "turn-down difference"])
        tou_43_header = find_tou_header(["tariff name", "average capacity"])

        tou_41 = parse_tou_table_41(tou_41_header) if tou_41_header is not None else pd.DataFrame()
        tou_42 = parse_tou_table_42(tou_42_header) if tou_42_header is not None else pd.DataFrame()
        tou_43 = parse_tou_table_43(tou_43_header) if tou_43_header is not None else pd.DataFrame()

        services_df = pd.DataFrame()
        if not tou_41.empty or not tou_42.empty or not tou_43.empty:
            services_df = tou_41.copy() if not tou_41.empty else pd.DataFrame(columns=["tariff_name"])
            if services_df.empty and not tou_42.empty:
                services_df = tou_42[["tariff_name"]].copy()
            if services_df.empty and not tou_43.empty:
                services_df = tou_43[["tariff_name"]].copy()

            for other in [tou_42, tou_43]:
                if other is None or other.empty:
                    continue
                services_df = services_df.merge(other, how="outer", on="tariff_name")

            services_df["service_type"] = "tou_tariff"

            # Ensure expected columns exist even when Part 4.3 is missing.
            # Downstream code relies on these fields being present.
            for col in [
                "unmanaged_customers",
                "managed_assets",
                "total_turn_down_mwh",
                "total_turn_up_mwh",
                "busiest_hh_turn_down_mwh",
                "busiest_hh_turn_up_mwh",
                "busiest_hh_turn_down_mw",
                "busiest_hh_turn_up_mw",
                "capacity_mw",
                "capacity_basis",
            ]:
                if col not in services_df.columns:
                    services_df[col] = None
        if services_df.empty:
            warnings.append("Template V1.2: no Part 4 ToU tables were populated")
        elif not services_df.empty:
            # Supplier submissions often provide Part 4.2 (period totals) without Part 4.3 (busiest HH),
            # which means we can use their ToU data for *energy* totals but cannot derive MW capacity.
            totals_present = False
            for c in ["total_turn_down_mwh", "total_turn_up_mwh"]:
                if c in services_df.columns and pd.to_numeric(services_df[c], errors="coerce").notna().any():
                    totals_present = True
                    break

            busiest_present = False
            for c in ["busiest_hh_turn_down_mw", "busiest_hh_turn_up_mw", "capacity_mw"]:
                if c in services_df.columns and pd.to_numeric(services_df[c], errors="coerce").notna().any():
                    busiest_present = True
                    break

            if totals_present and not busiest_present:
                warnings.append(
                    "Template V1.2: Part 4.2 ToU totals provided but Part 4.3 busiest-HH MW is missing; "
                    "implicit capacity (MW) cannot be derived (energy totals will still be used)."
                )

        sectors_present = set(assets_df['sector'].dropna().unique()) if not assets_df.empty and 'sector' in assets_df.columns else set()
        if sectors_present == {'domestic'}:
            sector_summary = 'domestic'
        elif sectors_present == {'ic'}:
            sector_summary = 'ic'
        elif sectors_present == {'domestic', 'ic'}:
            sector_summary = 'mixed'
        else:
            sector_summary = 'unknown'

        capacity_rows = assets_df['capacity_mw'].notna().sum() if not assets_df.empty and 'capacity_mw' in assets_df.columns else 0
        capacity_source = 'provided_3.2' if capacity_rows > 0 else 'missing_3.2'
        if capacity_rows == 0:
            warnings.append('Template V1.2: no numeric MW capacity values found in section 3.2; capacity treated as missing')

        return ParsedData(
            contributor_id=contributor_id,
            contributor_name=contributor_name,
            submission_date=datetime.now(),
            template_version='V1.2',
            sector=sector_summary,
            assets=assets_df,
            events=pd.DataFrame(),
            services=services_df,
            metadata={'format': 'ade_template_v1.2', 'capacity_source': capacity_source},
            parse_warnings=warnings,
            parse_errors=errors,
        )

    def _parse_ade_template(self, filepath: Path, contributor_id: str, name: str, default_sector: str) -> ParsedData:
        """Parse ADE template V1.2 format with complex structure."""
        try:
            df = pd.read_excel(filepath, sheet_name=0, header=None)

            assets = []

            # Look for the "Assets" row which contains headers
            asset_row_idx = None
            for idx, row in df.iterrows():
                row_str = ' '.join([str(v) for v in row if pd.notna(v)]).lower()
                if 'assets' in row_str and 'portfolio' in row_str:
                    asset_row_idx = idx
                    break

            if asset_row_idx is not None:
                # Parse asset data below the header
                for idx in range(asset_row_idx + 1, min(asset_row_idx + 20, len(df))):
                    row = df.iloc[idx]
                    # Look for asset type in column 12 (typical template position)
                    asset_type = None
                    count = None

                    for col_idx, val in enumerate(row):
                        if pd.notna(val):
                            val_str = str(val).lower()
                            # Check for known asset types
                            if any(at in val_str for at in ['ev', 'charger', 'heat pump', 'battery', 'bess', 'storage']):
                                asset_type = val_str
                            # Check for numeric counts
                            elif isinstance(val, (int, float)) and 0 < val < 10000000:
                                count = int(val)

                    if asset_type and count:
                        asset_class = self._map_asset_type(asset_type)
                        assets.append({
                            'asset_class': asset_class,
                            'sector': default_sector,
                            'count': count,
                            'capacity_mw': self._estimate_capacity(asset_class, count)
                        })

            # If no assets found via structure, try to find any EV charger counts
            if not assets:
                for idx, row in df.iterrows():
                    for col_idx, val in enumerate(row):
                        if isinstance(val, (int, float)) and not pd.isna(val) and 1000 < val < 10000000:
                            # Large number might be EV charger count
                            assets.append({
                                'asset_class': 'ev_charger',
                                'sector': default_sector,
                                'count': int(val),
                                'capacity_mw': self._estimate_capacity('ev_charger', int(val))
                            })
                            break
                    if assets:
                        break

            assets_df = pd.DataFrame(assets) if assets else pd.DataFrame()

        except Exception as e:
            logger.warning(f"{name} parse error: {e}")
            assets_df = pd.DataFrame()

        return ParsedData(
            contributor_id=contributor_id,
            contributor_name=name,
            submission_date=datetime.now(),
            template_version="V1.2",
            sector=default_sector,
            assets=assets_df,
            events=pd.DataFrame(),
            services=pd.DataFrame(),
            metadata={'format': 'ade_template_v1.2'},
            parse_warnings=[],
            parse_errors=[]
        )

    def _parse_generic(self, filepath: Path, contributor_id: str) -> ParsedData:
        """Generic parser for unknown formats."""
        logger.warning(f"Using generic parser for {filepath.name}")

        try:
            df = pd.read_excel(filepath, sheet_name=0, header=None)

            # Try to extract any meaningful data
            assets = []
            for idx, row in df.iterrows():
                for val in row:
                    if isinstance(val, (int, float)) and not pd.isna(val) and 100 < val < 10000000:
                        assets.append({
                            'asset_class': 'unknown',
                            'sector': 'unknown',
                            'count': int(val) if val > 100 else 1,
                            'capacity_mw': float(val) if val < 10000 else self._estimate_capacity('ev_charger', int(val))
                        })
                        break
                if assets:
                    break

            assets_df = pd.DataFrame(assets) if assets else pd.DataFrame()

        except Exception as e:
            logger.warning(f"Generic parse error: {e}")
            assets_df = pd.DataFrame()

        return ParsedData(
            contributor_id=contributor_id,
            contributor_name=filepath.stem,
            submission_date=datetime.now(),
            template_version="Unknown",
            sector="unknown",
            assets=assets_df,
            events=pd.DataFrame(),
            services=pd.DataFrame(),
            metadata={'format': 'generic'},
            parse_warnings=["Using generic parser - manual review recommended"],
            parse_errors=[]
        )

    def _map_asset_type(self, raw_type: str) -> str:
        """Map raw asset type string to standardized asset class."""
        raw_lower = raw_type.lower()

        if 'storage heater' in raw_lower or 'storage_heaters' in raw_lower:
            return 'storage_heater'
        if 'industrial load' in raw_lower:
            return 'industrial_load'
        if 'industrial' in raw_lower and 'manufactur' not in raw_lower:
            return 'industrial_load'
        if any(x in raw_lower for x in ['ev', 'charger', 'vehicle']):
            return 'ev_charger'
        elif any(x in raw_lower for x in ['heat pump', 'hp', 'ashp', 'gshp']):
            return 'heat_pump'
        elif any(x in raw_lower for x in ['cold', 'refriger', 'freezer']):
            return 'cold_storage'
        elif any(x in raw_lower for x in ['heat network', 'chp', 'thermal storage']):
            return 'heat_network_thermal'
        elif any(x in raw_lower for x in ['bess', 'battery', 'storage']):
            return 'battery_storage'
        elif any(x in raw_lower for x in ['hot water', 'immersion', 'heater']):
            return 'smart_hot_water'
        elif any(x in raw_lower for x in ['water treatment', 'sewage', 'wastewater']):
            return 'water_treatment'
        elif any(x in raw_lower for x in ['manufactur', 'factory']):
            return 'manufacturing'
        elif any(x in raw_lower for x in ['hvac', 'air condition', 'cooling']):
            return 'commercial_hvac'
        else:
            return 'other'

    def _map_industry_to_asset(self, industry: str) -> str:
        """Map industry type to asset class."""
        ind_lower = industry.lower()

        if 'food' in ind_lower or 'drink' in ind_lower:
            return 'cold_storage'
        elif 'water' in ind_lower:
            return 'water_treatment'
        elif 'manufact' in ind_lower or 'metal' in ind_lower:
            return 'manufacturing'
        elif 'chemical' in ind_lower:
            return 'manufacturing'
        elif 'energy' in ind_lower:
            return 'commercial_battery'
        elif 'recycl' in ind_lower:
            return 'manufacturing'
        else:
            return 'ic_mixed'

    def _estimate_capacity(self, asset_class: str, count: int) -> float:
        """Estimate MW capacity from asset count using typical ratings."""
        # Typical capacity per unit in kW
        typical_kw = {
            'ev_charger': 7.0,  # Average of 3.6-22 kW
            'heat_pump': 5.0,  # Average domestic HP
            'battery_storage': 5.0,  # Average home battery
            'smart_hot_water': 3.0,
            'cold_storage': 100.0,  # Per site
            'water_treatment': 500.0,  # Per site
            'manufacturing': 200.0,  # Per site
            'commercial_hvac': 50.0,
            'commercial_battery': 100.0,
            'ic_mixed': 100.0,
            'other': 5.0,
            'unknown': 5.0
        }

        kw_per_unit = typical_kw.get(asset_class, 5.0)
        return (count * kw_per_unit) / 1000  # Convert to MW


def parse_all_files(data_dir: Path, taxonomy: Dict = None) -> List[ParsedData]:
    """Parse all Excel files in a directory.

    Notes:
      - Prefers any `*_NORMALISED_V1.2.xlsx` files and skips their corresponding raw inputs
        to prevent double-counting.
      - Attempts to normalise non-template TOU returns into V1.2-shaped workbooks for
        consistent parsing (best-effort).
    """
    parser = TemplateParser(taxonomy=taxonomy)
    results: List[ParsedData] = []

    data_dir = Path(data_dir)

    def list_excel_files() -> List[Path]:
        files = list(data_dir.glob("*.xlsx")) + list(data_dir.glob("*.xls"))
        files = [p for p in files if not p.name.startswith("~$")]
        return sorted(files, key=lambda p: p.name.lower())

    excel_files = list_excel_files()

    # Normalise non-template TOU returns (best-effort).
    template_path = (data_dir.parent / "DATA REQUEST FORMS" / "Data Template V1.2.xlsx").resolve()
    try:
        from .tou_return_normaliser import normalise_tou_return_to_v1_2
    except Exception:
        normalise_tou_return_to_v1_2 = None

    if normalise_tou_return_to_v1_2 is not None and template_path.exists():
        for fp in excel_files:
            lower_stem = fp.stem.lower()
            if lower_stem.endswith("_normalised_v1.2") or lower_stem.endswith("_normalized_v1.2"):
                continue
            if not parser._looks_like_non_template_tou_return(fp):
                continue
            out_fp = fp.with_name(fp.stem + "_NORMALISED_V1.2" + fp.suffix)
            try:
                if (not out_fp.exists()) or (out_fp.stat().st_mtime < fp.stat().st_mtime):
                    normalise_tou_return_to_v1_2(raw_path=fp, template_path=template_path, output_path=out_fp)
                    logger.info(f"Normalised TOU return: {fp.name} -> {out_fp.name}")
            except Exception as e:
                logger.warning(f"TOU normalisation failed for {fp.name}: {e}")
    else:
        if normalise_tou_return_to_v1_2 is None:
            logger.info("TOU normaliser unavailable; skipping normalisation step")
        elif not template_path.exists():
            logger.info(f"Template V1.2 not found at {template_path}; skipping TOU normalisation step")

    # Refresh list after potential normalisation.
    excel_files = list_excel_files()

    # Skip raw files when a corresponding normalised file exists.
    raw_names_to_skip = set()
    for fp in excel_files:
        lower_stem = fp.stem.lower()
        for suffix in ("_normalised_v1.2", "_normalized_v1.2"):
            if lower_stem.endswith(suffix):
                raw_stem = fp.stem[: -len(suffix)]
                raw_names_to_skip.add((raw_stem + ".xlsx").lower())
                raw_names_to_skip.add((raw_stem + ".xls").lower())

    for filepath in excel_files:
        # Skip files in Notes subfolder (if any are passed explicitly).
        if "notes" in str(filepath.parent).lower():
            continue
        if filepath.name.lower() in raw_names_to_skip:
            logger.info(f"Skipping raw file because a normalised V1.2 version exists: {filepath.name}")
            continue

        try:
            result = parser.parse_file(filepath)
            results.append(result)
            logger.info(f"Successfully parsed: {filepath.name}")
        except Exception as e:
            logger.error(f"Failed to parse {filepath.name}: {e}")

    return results
