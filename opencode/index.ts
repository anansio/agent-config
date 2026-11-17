import { join, resolve } from "node:path"
import { fileURLToPath } from "node:url"
import { Plugin, Skill } from "@opencode/plugin"
import { loadMcpServers, loadRules, loadSkills, RULES_SKILL } from "./lib.ts"

// resolve() trims the trailing separator that a directory URL carries, so expanded paths stay clean.
const root = resolve(fileURLToPath(new URL("..", import.meta.url)))

export default Plugin.define({
  id: "agent-config",
  async setup(ctx) {
    // Read the portable package before registering: transform callbacks are synchronous.
    const rules = await loadRules(join(root, "skills", RULES_SKILL))
    const skills = await loadSkills(join(root, "skills"), [RULES_SKILL])
    const servers = await loadMcpServers(root, {
      python: process.platform === "win32" ? "python" : undefined,
    })

    await ctx.session.hook("context", (event) => {
      event.system.push({ type: "text", text: rules })
    })

    await ctx.skill.transform((editor) => {
      for (const skill of skills) {
        editor.add({
          id: Skill.ID.make(skill.id),
          name: Skill.Name.make(skill.name),
          description: skill.description,
          path: Skill.Info.fields.path.make(skill.path),
          content: skill.body,
        })
      }
    })

    await ctx.mcp.transform((editor) => {
      for (const server of servers) editor.set(server.name, server.config)
    })
  },
})
