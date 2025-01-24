import { fixupConfigRules } from "@eslint/compat";
import typescriptEslint from "@typescript-eslint/eslint-plugin";
import tsParser from "@typescript-eslint/parser";
import globals from "globals";
import path from "node:path";
import { fileURLToPath } from "node:url";
import js from "@eslint/js";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const compat = new FlatCompat({
  baseDirectory: __dirname,
  recommendedConfig: js.configs.recommended,
  allConfig: js.configs.all,
});

export default [
  {
    ignores: [
      "**/dist",
      "charting_library/**",
      "package.json",
      "package-lock.json",
      "vite.config.ts",
    ],
  },
  ...fixupConfigRules(
    compat.extends(
      "eslint:recommended",
      "prettier",
      "plugin:react/recommended",
    ),
  ),
  {
    plugins: {
      "@typescript-eslint": typescriptEslint,
    },
    languageOptions: {
      globals: {
        ...globals.node,
        ...globals.browser,
      },
      parser: tsParser,
      ecmaVersion: 6,
      sourceType: "script",
      parserOptions: {
        project: true,
        tsconfigRootDir: "./",
      },
    },

    rules: {
      "no-unused-vars": "off",
      "@typescript-eslint/no-unused-vars": "off",
      "@typescript-eslint/consistent-type-imports": [
        2,
        {
          fixStyle: "separate-type-imports",
        },
      ],
      "@typescript-eslint/no-restricted-imports": [
        2,
        {
          paths: [
            {
              name: "react-redux",
              importNames: ["useSelector", "useStore", "useDispatch"],
              message:
                "Please use pre-typed versions from `src/app/hooks.ts` instead.",
            },
          ],
        },
      ],
    },
  },
  {
    files: ["**/*.{c,m,}{t,j}s", "**/*.{t,j}sx"],
  },
  {
    files: ["**/*{test,spec}.{t,j}s?(x)"],

    languageOptions: {
      globals: {
        ...globals.jest,
      },
    },
  },
];
