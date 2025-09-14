import { fixupConfigRules } from "@eslint/compat";
import typescriptEslint from "@typescript-eslint/eslint-plugin";
import tsParser from "@typescript-eslint/parser";
import globals from "globals";
import js from "@eslint/js";
import { FlatCompat } from "@eslint/eslintrc";

import { fileURLToPath } from 'url';
import path from 'path';

const _dirname = path.dirname(fileURLToPath(import.meta.url));
const compat = new FlatCompat({
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
        tsconfigRootDir: _dirname,
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
      // Allow React 17+ automatic JSX runtime
      "react/react-in-jsx-scope": "off",
    },
    settings: {
      react: {
        version: "detect",
        jsxRuntime: "automatic",
      },
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
