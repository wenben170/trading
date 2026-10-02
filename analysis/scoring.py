class SignalScorer:
    @staticmethod
    def calculate_score(
        htf_align: bool,
        ms_bias: bool,
        liquidity_sweep: bool,
        fvg_quality: str,
        ob_quality: str,
        dxy_confirm: bool,
        yield_confirm: bool,
        news_clear: bool
    ) -> tuple[int, str]:
        score = 0

        if htf_align: score += 20
        if ms_bias: score += 15
        if liquidity_sweep: score += 15

        if fvg_quality == "A+": score += 10
        elif fvg_quality == "A": score += 8
        elif fvg_quality == "B": score += 5

        if ob_quality == "A+": score += 10
        elif ob_quality == "A": score += 8

        if dxy_confirm: score += 10
        if yield_confirm: score += 10
        if news_clear: score += 10

        grade = "NO_TRADE"
        if score >= 90: grade = "A+"
        elif score >= 80: grade = "A"
        elif score >= 70: grade = "B"
        else: grade = "WEAK"

        return score, grade