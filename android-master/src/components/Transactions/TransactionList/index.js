import React from 'react';
import { FlatList } from 'react-native';
import Loader from '../../qubiqle/Loader';
import Transaction from '../Transaction';
import InvoiceEmpty from '../../qubiqle/InvoiceEmpty';

export default function TransactionList(props) {
  let {
    transactions
  } = props;
  const {
    loadNextPage, loading, firstLoad, onPress, style, emptyMessage
  } = props;
  if (!transactions) transactions = [];

  return (
    <FlatList
      style={style}
      data={transactions}
      renderItem={({ item, index }) => (
        <Transaction
          index={index}
          key={item.id.toString()}
          transaction={item}
          onPress={onPress}
        />
      )}
      onEndReached={() => {
        loadNextPage();
      }}
      ListFooterComponent={
        transactions.length
          ? (
            <Loader
              loading={loading}
            />
          ) : null
      }
      ListEmptyComponent={(
        <InvoiceEmpty
          loading={loading}
          message={emptyMessage}
        />
      )}
      refreshing={transactions.length !== 0 && firstLoad}
      onRefresh={() => loadNextPage(1)}
      keyExtractor={(item) => item.id.toString()}
    />
  );
}
