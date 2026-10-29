import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { MessageMarkdown } from "../lib/markdown";
describe("untrusted message markdown", () => {
  it("disables raw HTML and unsafe URL protocols", () => {
    const html = renderToStaticMarkup(
      <MessageMarkdown
        body={
          '<img src="x" onerror="alert(1)"/>\n\n[unsafe](javascript:alert)\n\n[safe](https://example.invalid)'
        }
      />,
    );
    expect(html).not.toContain("onerror");
    expect(html).not.toContain("javascript:");
    expect(html).toContain('href="https://example.invalid"');
    expect(html).toContain("noopener noreferrer");
  });
  it("keeps code blocks LTR and escapes script markup", () => {
    const html = renderToStaticMarkup(
      <MessageMarkdown body={"```html\n<script>fixture</script>\n```"} />,
    );
    expect(html).toContain('dir="ltr"');
    expect(html).toContain("&lt;script&gt;");
    expect(html).not.toContain("<script>");
  });
});
