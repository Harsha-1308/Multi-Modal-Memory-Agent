import re


class OutcomeClassifier:

    SUCCESS = "success"
    FAILURE = "failure"
    NEUTRAL = "neutral"

    SUCCESS_WORDS = {
        "passed",
        "pass",
        "success",
        "successful",
        "succeeded",
        "resolved",
        "fixed",
        "worked",
        "completed",
        "improved",
        "achieved",
    }

    FAILURE_WORDS = {
        "failed",
        "fail",
        "failure",
        "unsuccessful",
        "unsuccessfully",
        "blocked",
        "rejected",
        "broken",
        "regressed",
    }

    @staticmethod
    def tokenize(text: str):
        if not isinstance(text, str):
            raise TypeError("Outcome evidence must be a string.")

        return set(
            re.findall(
                r"\b[a-z0-9]+\b",
                text.lower(),
            )
        )

    def classify(self, evidence: str) -> str:

        tokens = self.tokenize(evidence)

        has_success = bool(
            tokens.intersection(self.SUCCESS_WORDS)
        )

        has_failure = bool(
            tokens.intersection(self.FAILURE_WORDS)
        )

        # Conflicting evidence should not be
        # arbitrarily classified as success/failure.
        if has_success and has_failure:
            return self.NEUTRAL

        if has_success:
            return self.SUCCESS

        if has_failure:
            return self.FAILURE

        return self.NEUTRAL