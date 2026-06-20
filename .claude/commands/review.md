Review the current code changes for quality and correctness.

1. Run `git diff` to see all unstaged changes and `git diff --cached` for staged changes
2. Check each changed file for:
   - **Provider pattern**: AI calls must go through `WitService`, never direct SDK calls in views
   - **Rate limiting**: All public endpoints must use `AnonRateThrottle`
   - **Error handling**: Provider errors should be caught gracefully
   - **Security**: No hardcoded API keys, no exposed secrets, proper input validation
   - **Style**: Consistent with black/isort formatting, follows existing patterns
   - **Tests**: New functionality should have corresponding tests
3. Run `make lint` to catch formatting issues
4. Run `make test` to verify nothing is broken
5. Provide a summary of findings with actionable suggestions
