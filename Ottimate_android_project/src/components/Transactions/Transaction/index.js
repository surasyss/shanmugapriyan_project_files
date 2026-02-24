import React from 'react';
import {
  Text, TouchableOpacity, View
} from 'react-native';
import styles from './styles';

import { toCurrency } from '../../../utils/StringFormatter';
import { parseTransactionDate } from '../../../utils/DateFormatter';

export default class Transaction extends React.PureComponent {
  render() {
    const {
      transaction, onPress, index
    } = this.props;

    if (transaction) {
      const {
        merchant_name, card, posting_date, additional_info, computed_amount
      } = transaction;
      const { last_4, owner } = card;
      const { status, is_credit } = additional_info;

      return (
        <TouchableOpacity
          style={styles.mainView}
          onPress={() => {
            if (onPress) {
              onPress(index);
            }
          }}
        >
          <View style={styles.container}>
            <View style={styles.leftView}>
              <Text style={styles.vendorName}>{merchant_name || 'No Vendor Info'}</Text>
              <Text style={styles.userName}>{`${owner.display_name}    ****${last_4}`}</Text>
              <Text style={styles.date}>{parseTransactionDate(posting_date)}</Text>
            </View>

            <View style={styles.rightView}>
              <Text style={styles.amount}>{toCurrency(computed_amount)}</Text>
              <Text style={[styles.status, is_credit ? styles.credit : {}]}>{is_credit ? 'Refund' : status}</Text>
            </View>
          </View>

        </TouchableOpacity>
      );
    }
    return <View />;
  }
}
