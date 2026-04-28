export type ParsedRepo = {
  owner: string;
  name: string;
};

const pattern = /^https?:\/\/github\.com\/(?<owner>[A-Za-z0-9_.-]+)\/(?<name>[A-Za-z0-9_.-]+)\/?$/i;

export function parseGithubRepoUrl(repoUrl: string): ParsedRepo {
  const text = repoUrl.trim();
  const match = pattern.exec(text);
  if (!match?.groups?.owner || !match.groups.name) {
    throw new Error("Expected a URL like https://github.com/owner/name");
  }
  const owner = match.groups.owner;
  const name = match.groups.name.replace(/\.git$/i, "");
  return { owner, name };
}
