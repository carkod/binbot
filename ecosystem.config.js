module.exports = {
  apps : [{
    name: 'binbot',
    script: 'app/__main__.py',

    // Options reference: https://pm2.io/doc/en/runtime/reference/ecosystem-file/
    args: '--interpreter ~/miniconda/envs/binboardv1/bin/python',
    //exec_interpreter: '~/miniconda/envs/test1/bin/python',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '500M',
  }],

  deploy : {
    production : {
      user : 'node',
      host : '212.83.163.1',
      ref  : 'origin/master',
      repo : 'carkod@github.com:binboard.git',
      path : '/var/www/binboard',
      'post-deploy' : 'pm2 reload ecosystem.config.js --env production'
    }
  }
};
