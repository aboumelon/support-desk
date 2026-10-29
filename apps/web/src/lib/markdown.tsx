import Markdown from "react-markdown";
export function MessageMarkdown({ body }: { body: string }) {
  return (
    <div className="markdown">
      <Markdown
        skipHtml
        urlTransform={(url) => {
          try {
            const parsed = new URL(url, "https://supportdesk.invalid");
            return ["https:", "http:", "mailto:"].includes(parsed.protocol)
              ? url
              : "";
          } catch {
            return "";
          }
        }}
        components={{
          p: ({ children }) => <p dir="auto">{children}</p>,
          pre: ({ children }) => <pre dir="ltr">{children}</pre>,
          img: ({ alt }) => <span>{alt}</span>,
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noopener noreferrer">
              {children}
            </a>
          ),
        }}
      >
        {body}
      </Markdown>
    </div>
  );
}
