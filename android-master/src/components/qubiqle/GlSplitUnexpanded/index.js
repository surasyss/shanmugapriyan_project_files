import React from 'react';
import { Text, View } from 'react-native';
import styles from './styles';

import { title, toCurrencyNoSpace } from '../../../utils/StringFormatter';

export default function GlSplitUnexpanded(props) {
  const { invoice } = props;

  if (invoice) {
    let account_name = '';
    const { account, amount } = invoice;
    if (account) account_name = `${account.account_name} (${account.account_number})`;
    account_name = title(account_name.trim());

    return (
      <View style={styles.mainView}>
        <View style={styles.container}>
          <View style={styles.leftView}>
            <Text style={[styles.itemName, account_name ? {} : styles.missingValue]}>{account_name || 'Missing GL Split'}</Text>
          </View>
          <View style={styles.rightView}>
            <Text style={styles.quantity}>
              {toCurrencyNoSpace(amount)}
            </Text>
          </View>
        </View>

      </View>
    );
  }
}
