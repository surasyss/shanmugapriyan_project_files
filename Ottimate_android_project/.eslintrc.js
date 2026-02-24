module.exports = {
    'extends': 'airbnb',
    'parser': 'babel-eslint',
    'env': {
        'jest': true,
        'browser': true,
    },
    'rules': {
        'no-use-before-define': 'off',
        'react/jsx-filename-extension': 'off',
        'react/prop-types': 'off',
        'comma-dangle': 'off',
        'react/destructuring-assignment': 'off',
        'react/no-unused-state': 'off',
        'react/jsx-no-bind': 'off',
        'react/no-string-refs': 'off',
        'react/jsx-props-no-spreading': 'off',
        'no-param-reassign': 'off',
        'no-case-declarations': 'off',
        'camelcase': 'off',
        'global-require': 'off',
        'new-cap': 'off',
        'max-len': 'off',
        'no-await-in-loop': 'off',
        'no-shadow': 'off',
        'import/no-cycle': 'off',
        'class-methods-use-this': 'off',
        'no-empty': 'off',
        'no-new': 'off',
        'no-plusplus': 'off'
    },
    'globals': {
        'fetch': false
    },
    'settings': {
        'import/resolver': {
            'node': {
                'extensions': ['.js', '.jsx', '.json', '.native.js']
            }
        }
    }
};
