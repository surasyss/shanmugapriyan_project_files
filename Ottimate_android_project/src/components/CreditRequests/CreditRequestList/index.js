import React from 'react';
import { FlatList } from 'react-native';
import Loader from '../../qubiqle/Loader';
import InvoiceEmpty from '../../qubiqle/InvoiceEmpty';
import CreditRequest from '../CreditRequest';

export default function CreditRequestList(props) {
  let {
    creditRequests
  } = props;
  const {
    loadNextPage, loading, firstLoad, onPress, style, emptyMessage
  } = props;
  if (!creditRequests) creditRequests = [];

  return (
    <FlatList
      style={style}
      data={creditRequests}
      renderItem={({ item, index }) => (
        <CreditRequest
          index={index}
          key={item.id.toString()}
          creditRequest={item}
          onPress={onPress}
        />
      )}
      onEndReached={() => loadNextPage()}
      ListFooterComponent={
        creditRequests.length
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
      refreshing={creditRequests.length !== 0 && firstLoad}
      onRefresh={() => loadNextPage(1)}
      keyExtractor={(item) => item.id.toString()}
    />
  );
}
